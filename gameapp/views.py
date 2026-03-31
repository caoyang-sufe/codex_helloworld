from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render


BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


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
        }
    )

# Create your views here.
