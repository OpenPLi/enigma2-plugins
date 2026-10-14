W, H = 1280, 720

INK = 0x060912
DUSK = 0x0b1120
CARD = 0x101827
EDGE = 0x1c2740
WELL = 0x0a0f1b
LIFT = 0x17233a
GLASS = 0x141d31
CYAN = 0x22d3ee
VIOLET = 0x8b5cf6
TEXT = 0xeef2f8
MUTED = 0x8390a6
SOFT = 0xb8c4d6
GREEN = 0x34d399
AMBER = 0xfbbf24
RED = 0xf87171
BLUE = 0x60a5fa
YELLOW = 0xfacc15
WHITE = 0xffffff

KEYS = ((40, RED), (330, GREEN), (620, YELLOW), (910, BLUE))

FRAME = (
    ("fill", 0, 0, W, 88, DUSK, 0),
    ("glow", 0, 88, W, 2, CYAN, 0),
    ("fill", 0, 668, W, 52, DUSK, 0),
    ("fill", 300, 22, 1, 44, EDGE, 0),
)

TILE_W, TILE_H, GAP = 292, 168, 16
TILE_X, TILE_Y = 32, 296


def tile(index):
    col, row = index % 4, index // 4
    return TILE_X + col * (TILE_W + GAP), TILE_Y + row * (TILE_H + GAP)


HERO = (32, 104, 1216, 176)
STATS = ((800, 124), (952, 124), (1104, 124))
STAT_W, STAT_H = 136, 136
BUSY = (32, 296, 1216, 352)
WELL_BOX = (624, 316, 600, 316)

PANELS = {
    "main": (
        ("hero",) + HERO + (CARD, 20),
    ) + tuple(("stat", x, y, STAT_W, STAT_H, GLASS, 16) for x, y in STATS),
    "browser": (
        ("card", 32, 156, 1216, 444, CARD, 20),
        ("head", 32, 156, 1216, 42, LIFT, 20),
        ("card", 32, 608, 1216, 46, CARD, 16),
    ),
    "signal": (
        ("hero", 32, 104, 1216, 212, CARD, 20),
        ("card", 32, 332, 1216, 316, CARD, 20),
        ("well", 56, 352, 1168, 196, WELL, 16),
    ),
    "manage": (
        ("card", 32, 104, 560, 544, CARD, 20),
        ("hero", 608, 104, 640, 544, CARD, 20),
        ("fill", 632, 166, 48, 4, CYAN, 2),
    ),
    "settings": (
        ("card", 32, 104, 1216, 428, CARD, 20),
        ("hero", 32, 548, 1216, 100, CARD, 20),
        ("fill", 52, 574, 4, 48, CYAN, 2),
    ),
    "auto": (
        ("card", 32, 104, 1216, 330, CARD, 20),
        ("hero", 32, 450, 392, 198, CARD, 20),
        ("hero", 444, 450, 392, 198, CARD, 20),
        ("hero", 856, 450, 392, 198, CARD, 20),
    ),
    "report": (
        ("card", 32, 104, 1216, 544, CARD, 20),
    ),
}

ICONS = ("scan", "bolt", "list", "signal", "clock", "box", "gear", "doc", "trash", "undo", "erase", "refresh", "disk")
ROW = {"manage": 76}
ICON = 28
BIG = 40

COLOR_NAMES = ("INK", "DUSK", "CARD", "EDGE", "WELL", "LIFT", "GLASS", "CYAN", "VIOLET", "TEXT", "MUTED", "SOFT",
               "GREEN", "AMBER", "RED", "BLUE", "YELLOW", "WHITE")
