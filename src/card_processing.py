import re
from .config import CONDITION_MAP
from .data_processing import (
    normalize_key, find_best_match, enhance_matches_with_scryfall,
    get_market_price, create_scryfall_fallback_entry
)
from .data_processing import is_double_sided_candidate


given_up_cards = []
scryfall_only_cards = []
confirmed_matches = {}
pending_confirmations = []


def build_standard_entry(ref_row, product_name_suffix, manabox_row, condition):
    return {
        "TCGplayer Id": ref_row.get("TCGplayer Id", "Not Found"),
        "Product Line": ref_row.get("Product Line", "Magic: The Gathering"),
        "Set Name": ref_row.get("Set Name", ""),
        "Product Name": ref_row.get("Product Name", "") + product_name_suffix,
        "Number": ref_row.get("Number", ""),
        "Rarity": ref_row.get("Rarity", ""),
        "Condition": condition,
        "Add to Quantity": int(manabox_row.get("Quantity", "1")),
        "TCG Marketplace Price": manabox_row.get("Purchase price", "0.00")
    }


def build_token_entry(ref_row, token_set_name, token_product_name, token_number, manabox_row, condition):
    return {
        "TCGplayer Id": ref_row.get("TCGplayer Id", "Not Found"),
        "Product Line": ref_row.get("Product Line", "Magic: The Gathering"),
        "Set Name": ref_row.get("Set Name", token_set_name),
        "Product Name": ref_row.get("Product Name", token_product_name),
        "Number": ref_row.get("Number", token_number),
        "Rarity": ref_row.get("Rarity", "Token"),
        "Condition": condition,
        "Add to Quantity": int(manabox_row.get("Quantity", "1")),
        "TCG Marketplace Price": get_market_price(manabox_row, ref_row)
    }


def build_token_fallback(token_set_name, token_product_name, card_number, manabox_row, condition):
    fallback_price = get_market_price(manabox_row, None)
    return {
        "TCGplayer Id": "Not Found",
        "Product Line": "Magic: The Gathering",
        "Set Name": token_set_name,
        "Product Name": token_product_name,
        "Number": card_number,
        "Rarity": "Token",
        "Condition": condition,
        "Add to Quantity": int(manabox_row.get("Quantity", "1")),
        "TCG Marketplace Price": fallback_price
    }


def build_given_up_entry(manabox_row, condition, card_name, set_name):
    return {
        "TCGplayer Id": "Not Found",
        "Product Line": "Magic: The Gathering",
        "Set Name": set_name,
        "Product Name": card_name,
        "Number": manabox_row.get("Collector number", "").strip(),
        "Rarity": manabox_row.get("Rarity", ""),
        "Condition": condition,
        "Add to Quantity": int(manabox_row.get("Quantity", "1")),
        "TCG Marketplace Price": get_market_price(manabox_row, None)
    }


def confirm_and_iterate_match(normalized_key, matches, ref_data):
    best_match, best_score = matches[0]
    candidate = ref_data.get(best_match, {})
    second_best_score = matches[1][1] if len(matches) > 1 else 0
    is_scryfall_only = candidate.get("TCGplayer Id") == "Scryfall Verified"
    
    if best_score >= 270 and not is_scryfall_only:
        confirmed_matches[normalized_key] = best_match
        return best_match
    
    if best_score >= 260 and not is_scryfall_only and (best_score - second_best_score) >= 30:
        confirmed_matches[normalized_key] = best_match
        return best_match
    
    if is_scryfall_only and best_score >= 350:
        confirmed_matches[normalized_key] = best_match
        return best_match
    
    pending_confirmations.append((normalized_key, matches, ref_data))
    return None


def process_standard(manabox_row, card_database, condition, card_name, set_name):
    card_number = re.sub(r"^[A-Za-z\-]*", "", manabox_row.get("Collector number", "").strip().split("-")[-1])
    
    if not card_name or not set_name:
        return None
    
    normalized_result = normalize_key(card_name, set_name, condition, card_number)
    if not normalized_result:
        return None
    
    key = normalized_result[:4]
    
    if key in confirmed_matches:
        ref_row = card_database[confirmed_matches[key]]
        return build_standard_entry(ref_row, normalized_result[4], manabox_row, condition)
    
    matches = find_best_match(key, card_database, card_database)
    
    if not matches or (matches and matches[0][1] < 260):
        matches = enhance_matches_with_scryfall(normalized_result, matches, card_database, manabox_row)
    
    confirmed_match = None
    if matches:
        confirmed_match = confirm_and_iterate_match(key, matches, card_database)
    
    if confirmed_match:
        ref_row = card_database[confirmed_match]
        if ref_row.get("TCGplayer Id") == "Scryfall Verified":
            scryfall_entry = build_standard_entry(ref_row, normalized_result[4], manabox_row, condition)
            scryfall_only_cards.append(scryfall_entry)
            return None
        
        return build_standard_entry(ref_row, normalized_result[4], manabox_row, condition)
    
    if not any(item[0] == key for item in pending_confirmations):
        fallback = build_given_up_entry(manabox_row, condition, card_name, set_name)
        given_up_cards.append(fallback)
    
    return None


def process_token(manabox_row, card_database, condition, card_name, set_name):
    if set_name.startswith("T") and re.match(r"^T[A-Z0-9]+$", set_name):
        token_set_name = set_name[1:] + " tokens"
    else:
        token_set_name = set_name
    
    token_set_base = token_set_name.lower().replace(" tokens", "")
    card_number = manabox_row.get("Collector number", "").strip()
    
    if "//" in card_name:
        parts = card_name.split("//")
        side1 = parts[0].strip()
        side2 = re.sub(r"double[-\s]?sided token", "", parts[1], flags=re.IGNORECASE).strip()
        token_product_name = f"{side1} // {side2}"
    else:
        token_product_name = card_name
    
    normalized_token_key = normalize_key(token_product_name, token_set_name, condition, card_number)
    if not normalized_token_key:
        print(f"Skipping invalid or prerelease token: {card_name} from set {set_name}")
        return None
    
    token_ref_data = {
        k: v for k, v in card_database.items()
        if (
            ("token" in v.get("Set Name", "").lower() or "token" in v.get("Product Name", "").lower()) and
            (token_set_name.lower() in v.get("Set Name", "").lower() or token_set_base in v.get("Set Name", "").lower())
        )
    }
    
    matches = find_best_match(normalized_token_key[:4], token_ref_data, token_ref_data)
    chosen_match = None
    
    if matches:
        best_match, best_score = matches[0]
        if best_score >= 250:
            chosen_match = best_match
        else:
            pending_confirmations.append((normalized_token_key, matches, token_ref_data))
            return None
    
    if chosen_match and "//" in card_name:
        ds_matches = [
            (m, s) for m, s in matches
            if is_double_sided_candidate(token_ref_data[m].get("Product Name", ""))
        ]
        if ds_matches and ds_matches[0][0] != chosen_match:
            pending_confirmations.append((normalized_token_key, ds_matches, token_ref_data))
            return None
    
    if chosen_match:
        ref_row = token_ref_data[chosen_match]
        token_product_name = ref_row.get("Product Name", token_product_name)
        token_number = ref_row.get("Number", card_number)
        return build_token_entry(ref_row, token_set_name, token_product_name, token_number, manabox_row, condition)
    
    if not any(item[0] == normalized_token_key[:4] for item in pending_confirmations):
        fallback = build_token_fallback(token_set_name, token_product_name, card_number, manabox_row, condition)
        given_up_cards.append(fallback)
    
    return None


def map_fields(manabox_row, card_database):
    card_name = manabox_row.get("Name", "").strip()
    set_name = manabox_row.get("Set name", "").strip()
    condition_code = manabox_row.get("Condition", "near mint").strip().lower().replace("_", " ")
    foil = "Foil" if manabox_row.get("Foil", "normal").lower() == "foil" else ""
    condition = CONDITION_MAP.get(condition_code, "Near Mint")
    
    if foil:
        condition += " Foil"
    
    is_token = (
        "token" in set_name.lower() or
        "token" in card_name.lower() or
        (set_name.startswith("T") and re.match(r"^T[A-Z0-9]+$", set_name))
    )
    
    if is_token:
        return process_token(manabox_row, card_database, condition, card_name, set_name)
    else:
        return process_standard(manabox_row, card_database, condition, card_name, set_name)


def get_pending_confirmations():
    return pending_confirmations


def clear_pending_confirmations():
    global pending_confirmations
    pending_confirmations.clear()


def get_given_up_cards():
    return given_up_cards


def get_scryfall_only_cards():
    return scryfall_only_cards


def get_confirmed_matches():
    return confirmed_matches
