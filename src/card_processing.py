"""
Card processing module for MTG Card Converter.

This module handles the conversion of ManaBox card data to TCGPlayer format,
including matching, validation, and entry creation.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from .config import (
    CONDITION_MAP, MATCHING_CONFIG, CARD_PROCESSING_CONFIG,
    DEFAULT_PRODUCT_LINE, DEFAULT_TCGPLAYER_ID, DEFAULT_SCRYFALL_ID,
    DEFAULT_TOKEN_RARITY, DEFAULT_CONDITION, DEFAULT_QUANTITY
)
from .data_processing import (
    normalize_key, find_best_match, enhance_matches_with_scryfall,
    get_market_price, is_double_sided_candidate
)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ProcessingState:
    """Centralized state management for card processing."""
    given_up_cards: List[Dict[str, Any]]
    scryfall_only_cards: List[Dict[str, Any]]
    confirmed_matches: Dict[Tuple, Any]
    pending_confirmations: List[Tuple]
    
    def __init__(self):
        self.given_up_cards = []
        self.scryfall_only_cards = []
        self.confirmed_matches = {}
        self.pending_confirmations = []


# Global state instance
state = ProcessingState()


# =============================================================================
# ENTRY BUILDING
# =============================================================================

def build_card_entry(
    manabox_row: Dict[str, Any],
    condition: str,
    ref_row: Optional[Dict[str, Any]] = None,
    **overrides: str
) -> Dict[str, Any]:
    """
    Build card entries with flexible override support.
    
    Args:
        manabox_row: Source data from ManaBox
        condition: Card condition
        ref_row: Reference data (optional)
        **overrides: Override values (product_name, set_name, number, rarity, tcgplayer_id)
    
    Returns:
        Dictionary representing a TCGPlayer card entry
    """
    config = CARD_PROCESSING_CONFIG
    
    # Helper function to get value with fallbacks
    def get_value(field_name: str, override: Optional[str] = None) -> str:
        if override:
            return override
        if ref_row and field_name.startswith('ref_'):
            return ref_row.get(getattr(config, field_name), "")
        if field_name.startswith('manabox_'):
            return manabox_row.get(getattr(config, field_name), "")
        return ""
    
    return {
        "TCGplayer Id": overrides.get('tcgplayer_id', DEFAULT_TCGPLAYER_ID),
        "Product Line": DEFAULT_PRODUCT_LINE,
        "Set Name": get_value('ref_set_name_field', overrides.get('set_name')),
        "Product Name": get_value('ref_product_name_field', overrides.get('product_name')),
        "Number": get_value('ref_number_field', overrides.get('number')),
        "Rarity": get_value('ref_rarity_field', overrides.get('rarity')),
        "Condition": condition,
        "Add to Quantity": int(manabox_row.get(config.manabox_quantity_field, DEFAULT_QUANTITY)),
        "TCG Marketplace Price": get_market_price(manabox_row, ref_row)
    }


# =============================================================================
# MATCHING LOGIC
# =============================================================================

def confirm_and_iterate_match(normalized_key, matches, ref_data):
    """Simplified match confirmation logic."""
    best_match, best_score = matches[0]
    candidate = ref_data.get(best_match, {})
    second_best_score = matches[1][1] if len(matches) > 1 else 0
    is_scryfall_only = candidate.get("TCGplayer Id") == DEFAULT_SCRYFALL_ID
    
    # Simplified auto-confirmation logic
    should_confirm = (
        (is_scryfall_only and best_score >= MATCHING_CONFIG.scryfall_score) or
        (best_score >= MATCHING_CONFIG.high_confidence_score) or
        (best_score >= MATCHING_CONFIG.medium_confidence_score and 
         (best_score - second_best_score) >= MATCHING_CONFIG.score_difference_threshold)
    )
    
    if should_confirm:
        state.confirmed_matches[normalized_key] = best_match
        return best_match
    
    state.pending_confirmations.append((normalized_key, matches, ref_data))
    return None


# =============================================================================
# CARD PROCESSING
# =============================================================================

def extract_card_number(manabox_row: Dict[str, Any]) -> str:
    """Extract and clean card number from ManaBox data."""
    collector_number = manabox_row.get("Collector number", "").strip()
    return re.sub(r"^[A-Za-z\-]*", "", collector_number.split("-")[-1])


def is_token_card(card_name: str, set_name: str) -> bool:
    """Determine if a card is a token."""
    return (
        "token" in set_name.lower() or
        "token" in card_name.lower() or
        (set_name.startswith("T") and re.match(r"^T[A-Z0-9]+$", set_name))
    )


def process_card(manabox_row: Dict[str, Any], card_database: Dict, condition: str, 
                card_name: str, set_name: str, is_token: bool = False) -> Optional[Dict[str, Any]]:
    """Unified card processing function."""
    card_number = extract_card_number(manabox_row)
    
    if not card_name or not set_name:
        return None
    
    # Handle token-specific processing
    if is_token:
        return _process_token_card(manabox_row, card_database, condition, card_name, set_name, card_number)
    
    # Standard card processing
    normalized_result = normalize_key(card_name, set_name, condition, card_number)
    if not normalized_result:
        return None
    
    key = normalized_result[:4]
    
    # Check for existing confirmed match
    if key in state.confirmed_matches:
        ref_row = card_database[state.confirmed_matches[key]]
        product_name = ref_row.get("Product Name", "") + normalized_result[4]
        return build_card_entry(manabox_row, condition, ref_row, product_name=product_name)
    
    # Find matches
    matches = find_best_match(key, card_database, card_database)
    
    # Enhance with Scryfall if needed
    if not matches or (matches and matches[0][1] < MATCHING_CONFIG.medium_confidence_score):
        matches = enhance_matches_with_scryfall(normalized_result, matches, card_database, manabox_row)
    
    # Process matches
    confirmed_match = None
    if matches:
        confirmed_match = confirm_and_iterate_match(key, matches, card_database)
    
    if confirmed_match:
        ref_row = card_database[confirmed_match]
        if ref_row.get("TCGplayer Id") == DEFAULT_SCRYFALL_ID:
            product_name = ref_row.get("Product Name", "") + normalized_result[4]
            scryfall_entry = build_card_entry(manabox_row, condition, ref_row, product_name=product_name)
            state.scryfall_only_cards.append(scryfall_entry)
            return None
        product_name = ref_row.get("Product Name", "") + normalized_result[4]
        return build_card_entry(manabox_row, condition, ref_row, product_name=product_name)
    
    # Add to given up if not already pending
    if not any(item[0] == key for item in state.pending_confirmations):
        fallback = build_card_entry(manabox_row, condition, product_name=card_name, set_name=set_name)
        state.given_up_cards.append(fallback)
    
    return None


def _process_token_card(manabox_row: Dict[str, Any], card_database: Dict, condition: str, 
                       card_name: str, set_name: str, card_number: str) -> Optional[Dict[str, Any]]:
    """Process token cards with specialized logic."""
    # Determine token set name
    if set_name.startswith("T") and re.match(r"^T[A-Z0-9]+$", set_name):
        token_set_name = set_name[1:] + " tokens"
    else:
        token_set_name = set_name
    
    # Handle double-sided tokens
    if "//" in card_name:
        parts = card_name.split("//")
        side1 = parts[0].strip()
        side2 = re.sub(r"double[-\s]?sided token", "", parts[1], flags=re.IGNORECASE).strip()
        token_product_name = f"{side1} // {side2}"
    else:
        token_product_name = card_name
    
    # Filter database for tokens
    token_set_base = token_set_name.lower().replace(" tokens", "")
    token_ref_data = {
        k: v for k, v in card_database.items()
        if (
            ("token" in v.get("Set Name", "").lower() or "token" in v.get("Product Name", "").lower()) and
            (token_set_name.lower() in v.get("Set Name", "").lower() or token_set_base in v.get("Set Name", "").lower())
        )
    }
    
    # Use unified processing with token-specific database and lower threshold
    normalized_result = normalize_key(token_product_name, token_set_name, condition, card_number)
    
    if not normalized_result:
        print(f"Skipping invalid or prerelease token: {card_name} from set {set_name}")
        return None
    
    key = normalized_result[:4]
    
    # Check for existing confirmed match
    if key in state.confirmed_matches:
        ref_row = token_ref_data[state.confirmed_matches[key]]
        return build_card_entry(manabox_row, condition, ref_row,
                              product_name=ref_row.get("Product Name", token_product_name),
                              set_name=token_set_name,
                              number=ref_row.get("Number", card_number),
                              rarity=DEFAULT_TOKEN_RARITY)
    
    # Find matches with lower threshold for tokens
    matches = find_best_match(key, token_ref_data, token_ref_data)
    
    if not matches or (matches and matches[0][1] < MATCHING_CONFIG.token_score):
        # Add to given up if not already pending
        if not any(item[0] == key for item in state.pending_confirmations):
            fallback = build_card_entry(manabox_row, condition,
                                      product_name=token_product_name, set_name=token_set_name,
                                      number=card_number, rarity=DEFAULT_TOKEN_RARITY)
            state.given_up_cards.append(fallback)
        return None
    
    # Process matches
    chosen_match = None
    best_match, best_score = matches[0]
    if best_score >= MATCHING_CONFIG.token_score:
        chosen_match = best_match
    else:
        state.pending_confirmations.append((normalized_result, matches, token_ref_data))
        return None
    
    # Handle double-sided token special case
    if chosen_match and "//" in card_name:
        ds_matches = [
            (m, s) for m, s in matches
            if is_double_sided_candidate(token_ref_data[m].get("Product Name", ""))
        ]
        if ds_matches and ds_matches[0][0] != chosen_match:
            state.pending_confirmations.append((normalized_result, ds_matches, token_ref_data))
            return None
    
    if chosen_match:
        ref_row = token_ref_data[chosen_match]
        token_product_name = ref_row.get("Product Name", token_product_name)
        token_number = ref_row.get("Number", card_number)
        return build_card_entry(manabox_row, condition, ref_row,
                              product_name=token_product_name, set_name=token_set_name,
                              number=token_number, rarity=DEFAULT_TOKEN_RARITY)
    
    return None


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def map_fields(manabox_row, card_database):
    """Main entry point for processing ManaBox card data."""
    config = CARD_PROCESSING_CONFIG
    
    card_name = manabox_row.get(config.manabox_name_field, "").strip()
    set_name = manabox_row.get(config.manabox_set_field, "").strip()
    condition_code = manabox_row.get(config.manabox_condition_field, "near mint").strip().lower().replace("_", " ")
    foil = "Foil" if manabox_row.get(config.manabox_foil_field, "normal").lower() == "foil" else ""
    condition = CONDITION_MAP.get(condition_code, DEFAULT_CONDITION)
    
    if foil:
        condition += " Foil"
    
    # Process using unified approach
    is_token = is_token_card(card_name, set_name)
    return process_card(manabox_row, card_database, condition, card_name, set_name, is_token)


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

# Direct access to state for simplicity
given_up_cards = state.given_up_cards
scryfall_only_cards = state.scryfall_only_cards
confirmed_matches = state.confirmed_matches
pending_confirmations = state.pending_confirmations

# State management functions for external use
def get_pending_confirmations():
    return state.pending_confirmations

def clear_pending_confirmations():
    state.pending_confirmations.clear()

def get_given_up_cards():
    return state.given_up_cards

def get_scryfall_only_cards():
    return state.scryfall_only_cards

def get_confirmed_matches():
    return state.confirmed_matches


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

# Backward compatibility functions for external modules
def build_standard_entry(ref_row, product_name_suffix, manabox_row, condition):
    return build_card_entry(manabox_row, condition, ref_row, 
                          product_name=ref_row.get("Product Name", "") + product_name_suffix)

def build_token_entry(ref_row, token_set_name, token_product_name, token_number, manabox_row, condition):
    return build_card_entry(manabox_row, condition, ref_row,
                          product_name=token_product_name, set_name=token_set_name,
                          number=token_number, rarity=DEFAULT_TOKEN_RARITY)

def build_token_fallback(token_set_name, token_product_name, card_number, manabox_row, condition):
    return build_card_entry(manabox_row, condition,
                          product_name=token_product_name, set_name=token_set_name,
                          number=card_number, rarity=DEFAULT_TOKEN_RARITY)

def build_given_up_entry(manabox_row, condition, card_name, set_name):
    return build_card_entry(manabox_row, condition,
                          product_name=card_name, set_name=set_name)

def process_standard(manabox_row, card_database, condition, card_name, set_name):
    """Backward compatibility wrapper."""
    return process_card(manabox_row, card_database, condition, card_name, set_name, is_token=False)

def process_token(manabox_row, card_database, condition, card_name, set_name):
    """Backward compatibility wrapper."""
    return process_card(manabox_row, card_database, condition, card_name, set_name, is_token=True)