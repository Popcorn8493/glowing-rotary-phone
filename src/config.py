FILTER_PRERELEASE = False
FILTER_PROMO = False

SET_ALIAS = {
    "Universes Beyond: The Lord of the Rings: Tales of Middle-earth": "LTR",
    "Commander: The Lord of the Rings: Tales of Middle-earth": "LTC",
    "the list": "The List",
    "edge of eternities": "eoe",
    "EOE": "eoe"
}

CONDITION_MAP = {
    "near mint": "Near Mint",
    "lightly played": "Lightly Played",
    "moderately played": "Moderately Played",
    "heavily played": "Heavily Played",
    "damaged": "Damaged"
}

condition_rank = {
    "near mint": 0,
    "lightly played": 1,
    "moderately played": 2,
    "heavily played": 3,
    "damaged": 4
}

FLOOR_PRICE = 0.10

SCRYFALL_API_BASE = "https://api.scryfall.com"
SCRYFALL_RATE_LIMIT = 0.1

TCGPLAYER_FIELDS = [
    "TCGplayer Id", "Product Line", "Set Name", "Product Name",
    "Number", "Rarity", "Condition", "Add to Quantity", "TCG Marketplace Price"
]

SPECIAL_PRINT_PENALTIES = {
    "foil": 40,
    "showcase": 30,
    "etched": 30,
    "borderless": 30,
    "extended": 30,
    "gilded": 30
}

PROMO_PATTERNS = [
    r"\(Bundle\)", r"\(Buyabox\)", r"\(Buy-a-[Bb]ox\)", r"\(Promo\)",
    r"\(Release\)", r"\(Launch\)", r"\(Store Championship\)",
    r"\(Game Day\)", r"\(FNM\)", r"\(Judge\)"
]
