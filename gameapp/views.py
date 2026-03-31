import json
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .game_logic import GameEngine


BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ENGINE = GameEngine()


def _list_png_paths(folder: str) -> list[str]:
    target = ASSETS_DIR / folder
    if not target.is_dir():
        return []
    return sorted(
        f"/assets/{folder}/{item.name}"
        for item in target.iterdir()
        if item.is_file() and item.suffix.lower() == ".png"
    )


def game(request):
    return render(request, "gameapp/game.html")


def handbook(request):
    return render(request, "gameapp/handbook.html")


def api_cards(request):
    return JsonResponse(
        {
            "cards": _list_png_paths("card"),
            "pieces": _list_png_paths("piece"),
            "heroes": _list_png_paths("general"),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_game_new(request):
    payload = json.loads(request.body or "{}")
    hero_name = payload.get("hero_name", "default")
    game = ENGINE.new_game(hero_name=hero_name)
    return JsonResponse(ENGINE.serialize(game))


@csrf_exempt
@require_http_methods(["POST"])
def api_game_action(request):
    payload = json.loads(request.body or "{}")
    game_id = payload.get("game_id")
    action = payload.get("action")
    game = ENGINE.get(game_id)

    if action == "refresh":
        ENGINE.refresh_shop(game.players[0], force=False)
    elif action == "buy":
        ENGINE.buy_from_shop(game, int(payload.get("shop_index", -1)))
    elif action == "play":
        ENGINE.play_to_board(game, int(payload.get("hand_index", -1)), payload.get("board_index"))
    elif action == "sell":
        ENGINE.sell_from_hand(game, int(payload.get("hand_index", -1)))
    elif action == "lock":
        ENGINE.toggle_shop_lock(game, bool(payload.get("locked", False)))
    elif action == "upgrade":
        ENGINE.upgrade_tavern(game)
    elif action == "discover_pick":
        ENGINE.choose_discover(game, int(payload.get("option_index", -1)))
    elif action == "battle":
        ENGINE.end_recruit_and_battle(game)

    return JsonResponse(ENGINE.serialize(game))
