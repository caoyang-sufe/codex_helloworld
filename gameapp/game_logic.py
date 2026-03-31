from __future__ import annotations

import random
import uuid
from dataclasses import asdict, dataclass, field

from .config_loader import CardDef, GameConfig, load_game_config

MAX_ROUNDS = 25
PLAYER_COUNT = 8
BOARD_LIMIT = 7
HAND_LIMIT = 10
SHOP_SLOTS = 6
START_HEALTH = 40


@dataclass
class CardInstance:
    uid: str
    id: str
    name: str
    card_type: int
    tier: int
    attack: int
    health: int
    skill: str
    faction: str
    origin: str = "card"


@dataclass
class PlayerState:
    index: int
    is_human: bool
    hero_name: str
    health: int = START_HEALTH
    tavern_tier: int = 1
    gold: int = 0
    board: list[CardInstance] = field(default_factory=list)
    hand: list[CardInstance] = field(default_factory=list)
    shop: list[CardInstance] = field(default_factory=list)
    lock_shop: bool = False
    upgrade_discount: int = 0
    equipment: dict | None = None
    pending_discover: list[CardInstance] = field(default_factory=list)

    @property
    def alive(self) -> bool:
        return self.health > 0


@dataclass
class MatchState:
    game_id: str
    round_no: int = 0
    phase: str = "init"
    players: list[PlayerState] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    game_over: bool = False
    winner_index: int | None = None
    pending_opponent: int | None = None


class GameEngine:
    def __init__(self, config: GameConfig | None = None):
        self.config = config or load_game_config()
        self.games: dict[str, MatchState] = {}
        self.recruit_pool = [c for c in self.config.recruit_cards if c.card_type == 2]
        self.gold_mapping = {c.id: c for c in self.config.recruit_cards + self.config.derived_cards if c.card_type == 1}

    def new_game(self, hero_name: str = "default") -> MatchState:
        gid = uuid.uuid4().hex
        players = [
            PlayerState(index=idx, is_human=(idx == 0), hero_name=(hero_name if idx == 0 else f"AI-{idx}"))
            for idx in range(PLAYER_COUNT)
        ]
        game = MatchState(game_id=gid, players=players)
        self.games[gid] = game
        self.start_recruit_phase(game)
        return game

    def get(self, game_id: str) -> MatchState:
        return self.games[game_id]

    def start_recruit_phase(self, game: MatchState) -> None:
        game.round_no += 1
        game.phase = "recruit"
        if game.round_no > MAX_ROUNDS:
            self._finish_by_health(game)
            return

        human = game.players[0]
        human.gold += min(game.round_no + 2, 15)

        if game.round_no in {3, 7, 11}:
            human.equipment = asdict(random.choice(self.config.weapons))

        if not human.lock_shop:
            self.refresh_shop(human)
        human.lock_shop = False

        self._setup_ai_boards(game)
        game.logs.append(f"第{game.round_no}回合招募阶段开始。")

    def refresh_shop(self, player: PlayerState, force: bool = False) -> bool:
        if not force and player.gold < 1:
            return False
        if not force:
            player.gold -= 1
        player.shop = [self._draw_recruit_card(player.tavern_tier) for _ in range(SHOP_SLOTS)]
        return True

    def buy_from_shop(self, game: MatchState, shop_index: int) -> bool:
        player = game.players[0]
        if game.phase != "recruit" or not (0 <= shop_index < len(player.shop)):
            return False
        if player.gold < 3 or len(player.hand) >= HAND_LIMIT:
            return False
        card = player.shop[shop_index]
        if not card:
            return False
        player.gold -= 3
        player.hand.append(card)
        player.shop[shop_index] = self._draw_recruit_card(player.tavern_tier)
        self._resolve_triples(player)
        return True

    def play_to_board(self, game: MatchState, hand_index: int, board_index: int | None = None) -> bool:
        player = game.players[0]
        if game.phase != "recruit" or not (0 <= hand_index < len(player.hand)):
            return False
        if len(player.board) >= BOARD_LIMIT:
            return False
        card = player.hand.pop(hand_index)
        if board_index is None or board_index >= len(player.board):
            player.board.append(card)
        else:
            player.board.insert(max(0, board_index), card)
        self._resolve_triples(player)
        return True

    def sell_from_hand(self, game: MatchState, hand_index: int) -> bool:
        player = game.players[0]
        if game.phase != "recruit" or not (0 <= hand_index < len(player.hand)):
            return False
        card = player.hand.pop(hand_index)
        if card.origin != "spell":
            player.gold += 1
        self._resolve_triples(player)
        return True

    def toggle_shop_lock(self, game: MatchState, locked: bool) -> None:
        game.players[0].lock_shop = locked

    def upgrade_tavern(self, game: MatchState) -> bool:
        player = game.players[0]
        if player.tavern_tier >= 6:
            return False
        base = self.config.upgrade_costs[player.tavern_tier - 1]
        cost = max(0, base - player.upgrade_discount)
        if player.gold < cost:
            return False
        player.gold -= cost
        player.tavern_tier += 1
        player.upgrade_discount = 0
        self._give_upgrade_spell(player)
        return True

    def choose_discover(self, game: MatchState, option_index: int) -> bool:
        player = game.players[0]
        if not (0 <= option_index < len(player.pending_discover)):
            return False
        if len(player.hand) >= HAND_LIMIT:
            return False
        chosen = player.pending_discover[option_index]
        player.hand.append(chosen)
        player.pending_discover = []
        return True

    def end_recruit_and_battle(self, game: MatchState) -> None:
        if game.phase != "recruit" or game.game_over:
            return
        game.phase = "battle"

        human = game.players[0]
        self._apply_round_discount(human)

        alive_ai = [p for p in game.players[1:] if p.alive]
        if not alive_ai:
            game.game_over = True
            game.winner_index = 0
            return
        opponent = random.choice(alive_ai)
        opponent.tavern_tier = human.tavern_tier
        game.pending_opponent = opponent.index

        result = self._simulate_battle(human, opponent)
        if result == "human_loss":
            dmg = sum(card.tier for card in opponent.board) + opponent.tavern_tier
            human.health = max(0, human.health - dmg)
            game.logs.append(f"你战败，受到{dmg}点伤害，剩余{human.health}生命。")
        elif result == "ai_loss":
            dmg = sum(card.tier for card in human.board) + human.tavern_tier
            opponent.health = max(0, opponent.health - dmg)
            game.logs.append(f"你获胜，AI-{opponent.index}受到{dmg}点伤害。")
        else:
            game.logs.append("本回合平局，双方均不扣血。")

        self._check_elimination(game)
        if not game.game_over:
            self.start_recruit_phase(game)

    def serialize(self, game: MatchState) -> dict:
        return {
            "game_id": game.game_id,
            "round": game.round_no,
            "phase": game.phase,
            "game_over": game.game_over,
            "winner_index": game.winner_index,
            "pending_opponent": game.pending_opponent,
            "logs": game.logs[-12:],
            "players": [self._serialize_player(p) for p in game.players],
        }

    def _serialize_player(self, player: PlayerState) -> dict:
        return {
            "index": player.index,
            "is_human": player.is_human,
            "hero_name": player.hero_name,
            "health": player.health,
            "alive": player.alive,
            "tavern_tier": player.tavern_tier,
            "gold": player.gold,
            "lock_shop": player.lock_shop,
            "upgrade_discount": player.upgrade_discount,
            "board": [asdict(c) for c in player.board],
            "hand": [asdict(c) for c in player.hand],
            "shop": [asdict(c) for c in player.shop],
            "equipment": player.equipment,
            "pending_discover": [asdict(c) for c in player.pending_discover],
        }

    def _draw_recruit_card(self, tavern_tier: int) -> CardInstance:
        probs = self.config.shop_rank_prob.get(tavern_tier, [1, 0, 0, 0, 0, 0])
        tier = random.choices([1, 2, 3, 4, 5, 6], weights=probs, k=1)[0]
        choices = [c for c in self.recruit_pool if c.tier == tier] or self.recruit_pool
        return self._create_instance(random.choice(choices), origin="card")

    def _create_instance(self, card_def: CardDef, origin: str = "card") -> CardInstance:
        return CardInstance(
            uid=uuid.uuid4().hex[:10],
            id=card_def.id,
            name=card_def.name,
            card_type=card_def.card_type,
            tier=card_def.tier,
            attack=card_def.attack,
            health=card_def.health,
            skill=card_def.skill,
            faction=card_def.faction,
            origin=origin,
        )

    def _resolve_triples(self, player: PlayerState) -> None:
        if len(player.hand) + len(player.board) < 3:
            return

        while True:
            normal_cards = [
                c for c in (player.hand + player.board)
                if c.card_type == 2
            ]
            grouped: dict[str, list[CardInstance]] = {}
            for card in normal_cards:
                grouped.setdefault(card.id, []).append(card)

            triple_id = next((card_id for card_id, cards in grouped.items() if len(cards) >= 3), None)
            if not triple_id:
                return

            remove_uids = {c.uid for c in grouped[triple_id][:3]}
            player.hand = [c for c in player.hand if c.uid not in remove_uids]
            player.board = [c for c in player.board if c.uid not in remove_uids]

            gold_def = self.gold_mapping.get(triple_id)
            if gold_def and len(player.hand) < HAND_LIMIT:
                player.hand.append(self._create_instance(gold_def))

            discover_tier = min(6, player.tavern_tier + 1)
            discover_pool = [c for c in self.recruit_pool if c.tier == discover_tier]
            if not discover_pool:
                discover_pool = [c for c in self.recruit_pool if c.tier == player.tavern_tier]
            options = random.sample(discover_pool, k=min(3, len(discover_pool)))
            player.pending_discover = [self._create_instance(c) for c in options]

    def _setup_ai_boards(self, game: MatchState) -> None:
        human_tier = game.players[0].tavern_tier
        tier_pool = [c for c in self.recruit_pool if c.tier <= human_tier] or self.recruit_pool
        for ai in game.players[1:]:
            if not ai.alive:
                ai.board = []
                continue
            ai.tavern_tier = human_tier
            sample = random.choices(tier_pool, k=BOARD_LIMIT)
            ai.board = [self._create_instance(c) for c in sample]

    def _simulate_battle(self, human: PlayerState, ai: PlayerState) -> str:
        human_power = sum(c.attack + c.health for c in human.board)
        ai_power = sum(c.attack + c.health for c in ai.board)
        if human_power == ai_power:
            return random.choice(["draw", "draw", "ai_loss", "human_loss"])
        return "ai_loss" if human_power > ai_power else "human_loss"

    def _check_elimination(self, game: MatchState) -> None:
        living = [p for p in game.players if p.alive]
        if not game.players[0].alive:
            game.game_over = True
            game.winner_index = living[0].index if living else None
            return
        if len(living) == 1:
            game.game_over = True
            game.winner_index = living[0].index
            return
        if game.round_no >= MAX_ROUNDS:
            self._finish_by_health(game)

    def _finish_by_health(self, game: MatchState) -> None:
        game.game_over = True
        game.winner_index = max(game.players, key=lambda p: p.health).index

    def _apply_round_discount(self, player: PlayerState) -> None:
        if player.tavern_tier >= 6:
            return
        base = self.config.upgrade_costs[player.tavern_tier - 1]
        effective = max(0, base - player.upgrade_discount)
        effective = max(0, effective - 2)
        player.upgrade_discount = base - effective

    def _give_upgrade_spell(self, player: PlayerState) -> None:
        tier = player.tavern_tier
        candidates = [s for s in self.config.spells if s.tier == tier]
        if not candidates:
            return
        offer = random.sample(candidates, k=min(3, len(candidates)))
        if offer and len(player.hand) < HAND_LIMIT:
            pick = random.choice(offer)
            player.hand.append(
                CardInstance(
                    uid=uuid.uuid4().hex[:10],
                    id=pick.id,
                    name=pick.name,
                    card_type=0,
                    tier=pick.tier,
                    attack=0,
                    health=0,
                    skill=pick.skill,
                    faction="spell",
                    origin="spell",
                )
            )
