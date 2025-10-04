"""
Configuration settings for MTG Card Converter.

This module contains all configuration constants organized by functionality.
"""

from typing import Dict, List, NamedTuple
from dataclasses import dataclass


# =============================================================================
# FILTERING CONFIGURATION
# =============================================================================

FILTER_PRERELEASE: bool = False
FILTER_PROMO: bool = False


# =============================================================================
# CARD CONDITIONS
# =============================================================================

class CardCondition(NamedTuple):
    """Represents a card condition with its display name and ranking."""
    display_name: str
    rank: int


# Consolidated condition data - eliminates duplication between CONDITION_MAP and condition_rank
CARD_CONDITIONS: Dict[str, CardCondition] = {
    "near mint": CardCondition("Near Mint", 0),
    "lightly played": CardCondition("Lightly Played", 1),
    "moderately played": CardCondition("Moderately Played", 2),
    "heavily played": CardCondition("Heavily Played", 3),
    "damaged": CardCondition("Damaged", 4)
}

# Backward compatibility - these can be removed once all imports are updated
CONDITION_MAP: Dict[str, str] = {
    key: condition.display_name for key, condition in CARD_CONDITIONS.items()
}

condition_rank: Dict[str, int] = {
    key: condition.rank for key, condition in CARD_CONDITIONS.items()
}


# =============================================================================
# SET ALIASES
# =============================================================================

SET_ALIAS: Dict[str, str] = {
    "Universes Beyond: The Lord of the Rings: Tales of Middle-earth": "LTR",
    "Commander: The Lord of the Rings: Tales of Middle-earth": "LTC",
    "the list": "The List",
    "edge of eternities": "eoe",
    "EOE": "eoe"
}


# =============================================================================
# PRICING CONFIGURATION
# =============================================================================

FLOOR_PRICE: float = 0.10


# =============================================================================
# API CONFIGURATION
# =============================================================================

@dataclass
class ScryfallConfig:
    """Scryfall API configuration."""
    base_url: str = "https://api.scryfall.com"
    rate_limit: float = 0.1  # seconds between requests


SCRYFALL_CONFIG = ScryfallConfig()

# Backward compatibility
SCRYFALL_API_BASE: str = SCRYFALL_CONFIG.base_url
SCRYFALL_RATE_LIMIT: float = SCRYFALL_CONFIG.rate_limit


# =============================================================================
# TCGPLAYER CONFIGURATION
# =============================================================================

TCGPLAYER_FIELDS: List[str] = [
    "TCGplayer Id", "Product Line", "Set Name", "Product Name",
    "Number", "Rarity", "Condition", "Add to Quantity", "TCG Marketplace Price"
]


# =============================================================================
# MATCHING ALGORITHM CONFIGURATION
# =============================================================================

@dataclass
class MatchingConfig:
    """Configuration for card matching algorithm."""
    # Score thresholds for automatic confirmation
    high_confidence_score: int = 270
    medium_confidence_score: int = 260
    scryfall_score: int = 350
    token_score: int = 250
    score_difference_threshold: int = 30
    
    # Special print penalties
    special_print_penalties: Dict[str, int] = None
    promo_patterns: List[str] = None
    
    def __post_init__(self):
        if self.special_print_penalties is None:
            self.special_print_penalties = {
                "foil": 40,
                "showcase": 30,
                "etched": 30,
                "borderless": 30,
                "extended": 30,
                "gilded": 30
            }
        if self.promo_patterns is None:
            self.promo_patterns = [
                r"\(Bundle\)", r"\(Buyabox\)", r"\(Buy-a-[Bb]ox\)", r"\(Promo\)",
                r"\(Release\)", r"\(Launch\)", r"\(Store Championship\)",
                r"\(Game Day\)", r"\(FNM\)", r"\(Judge\)"
            ]


MATCHING_CONFIG = MatchingConfig()

# Backward compatibility
SPECIAL_PRINT_PENALTIES: Dict[str, int] = MATCHING_CONFIG.special_print_penalties
PROMO_PATTERNS: List[str] = MATCHING_CONFIG.promo_patterns

# Score thresholds for backward compatibility
HIGH_CONFIDENCE_SCORE: int = MATCHING_CONFIG.high_confidence_score
MEDIUM_CONFIDENCE_SCORE: int = MATCHING_CONFIG.medium_confidence_score
SCRYFALL_SCORE: int = MATCHING_CONFIG.scryfall_score
TOKEN_SCORE: int = MATCHING_CONFIG.token_score
SCORE_DIFFERENCE_THRESHOLD: int = MATCHING_CONFIG.score_difference_threshold


# =============================================================================
# CARD PROCESSING CONFIGURATION
# =============================================================================

@dataclass
class CardProcessingConfig:
    """Configuration for card processing operations."""
    # Default values
    default_product_line: str = "Magic: The Gathering"
    default_tcgplayer_id: str = "Not Found"
    default_scryfall_id: str = "Scryfall Verified"
    default_token_rarity: str = "Token"
    default_condition: str = "Near Mint"
    default_quantity: str = "1"
    
    # Field names for ManaBox data
    manabox_name_field: str = "Name"
    manabox_set_field: str = "Set code"
    manabox_condition_field: str = "Condition"
    manabox_foil_field: str = "Foil"
    manabox_quantity_field: str = "Quantity"
    manabox_collector_number_field: str = "Collector number"
    manabox_rarity_field: str = "Rarity"
    manabox_purchase_price_field: str = "Purchase price"
    
    # Field names for reference data
    ref_tcgplayer_id_field: str = "TCGplayer Id"
    ref_product_line_field: str = "Product Line"
    ref_set_name_field: str = "Set Name"
    ref_product_name_field: str = "Product Name"
    ref_number_field: str = "Number"
    ref_rarity_field: str = "Rarity"
    ref_condition_field: str = "Condition"


CARD_PROCESSING_CONFIG = CardProcessingConfig()

# Backward compatibility
DEFAULT_PRODUCT_LINE: str = CARD_PROCESSING_CONFIG.default_product_line
DEFAULT_TCGPLAYER_ID: str = CARD_PROCESSING_CONFIG.default_tcgplayer_id
DEFAULT_SCRYFALL_ID: str = CARD_PROCESSING_CONFIG.default_scryfall_id
DEFAULT_TOKEN_RARITY: str = CARD_PROCESSING_CONFIG.default_token_rarity
DEFAULT_CONDITION: str = CARD_PROCESSING_CONFIG.default_condition
DEFAULT_QUANTITY: str = CARD_PROCESSING_CONFIG.default_quantity
