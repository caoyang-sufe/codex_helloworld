from __future__ import annotations

import random

from .config_loader import CardDef


def generate_random_board(card_pool: list[CardDef], board_size: int = 7) -> list[CardDef]:
    if not card_pool:
        return []
    return random.choices(card_pool, k=board_size)
