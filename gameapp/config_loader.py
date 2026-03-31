from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configs"


@dataclass(frozen=True)
class CardDef:
    id: str
    name: str
    card_type: int
    faction: str
    gender: str
    tier: int
    attack: int
    health: int
    skill: str
    recruitable: bool


@dataclass(frozen=True)
class SpellDef:
    id: str
    name: str
    tier: int
    skill: str


@dataclass(frozen=True)
class WeaponDef:
    id: str
    name: str
    weapon_type: str
    skill: str


@dataclass(frozen=True)
class GameConfig:
    recruit_cards: list[CardDef]
    derived_cards: list[CardDef]
    spells: list[SpellDef]
    weapons: list[WeaponDef]
    entry_desc: dict[str, str]
    shop_rank_prob: dict[int, list[float]]
    upgrade_costs: list[int]


def _read_delimited(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def _to_card(rows: list[dict[str, str]], recruitable: bool) -> list[CardDef]:
    cards: list[CardDef] = []
    for row in rows:
        cards.append(
            CardDef(
                id=row["ID"].strip(),
                name=row["名称"].strip(),
                card_type=int(row["类型"]),
                faction=row["势力"].strip(),
                gender=row["性别"].strip(),
                tier=int(row["等级"]),
                attack=int(row["攻击"]),
                health=int(row["血量"]),
                skill=row["技能描述"].strip(),
                recruitable=recruitable,
            )
        )
    return cards


@lru_cache(maxsize=1)
def load_game_config() -> GameConfig:
    recruit_cards = _to_card(_read_delimited(CONFIG_DIR / "card.csv", delimiter="\t"), recruitable=True)
    derived_cards = _to_card(_read_delimited(CONFIG_DIR / "card_ex.csv", delimiter="\t"), recruitable=False)

    spell_rows = _read_delimited(CONFIG_DIR / "spell.csv", delimiter="\t")
    spells = [
        SpellDef(
            id=row["ID"].strip(),
            name=row["名称"].strip(),
            tier=int(row["等级"]),
            skill=row["技能描述"].strip(),
        )
        for row in spell_rows
    ]

    weapon_rows = _read_delimited(CONFIG_DIR / "weapon.csv", delimiter="\t")
    weapons = [
        WeaponDef(
            id=row["ID"].strip(),
            name=row["名称"].strip(),
            weapon_type=row["类型"].strip(),
            skill=row["技能描述"].strip(),
        )
        for row in weapon_rows
    ]

    entry_rows = _read_delimited(CONFIG_DIR / "entry_desc.csv", delimiter="\t")
    entry_desc = {row["词条"].strip(): row["词条描述"].strip() for row in entry_rows}

    prob_rows = _read_delimited(CONFIG_DIR / "shop_rank_prob.csv", delimiter="\t")
    shop_rank_prob: dict[int, list[float]] = {}
    for row in prob_rows:
        tier = int(row["等级"])
        probs = [float(row[f"概率{idx}"] or 0) for idx in range(1, 7)]
        total = sum(probs)
        shop_rank_prob[tier] = probs if total == 0 else [p / total for p in probs]

    with (CONFIG_DIR / "upgrade_shop_cost.txt").open("r", encoding="utf-8") as fh:
        upgrade_costs = [int(line.strip()) for line in fh if line.strip()]

    return GameConfig(
        recruit_cards=recruit_cards,
        derived_cards=derived_cards,
        spells=spells,
        weapons=weapons,
        entry_desc=entry_desc,
        shop_rank_prob=shop_rank_prob,
        upgrade_costs=upgrade_costs,
    )
