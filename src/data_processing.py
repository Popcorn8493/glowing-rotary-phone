import re
import unicodedata
from rapidfuzz import fuzz
from .config import (
    SET_ALIAS, CONDITION_MAP, condition_rank, FLOOR_PRICE, 
    SPECIAL_PRINT_PENALTIES, FILTER_PRERELEASE, FILTER_PROMO, PROMO_PATTERNS
)
from .scryfall_api import query_scryfall_card, query_scryfall_by_id


def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )


def is_double_sided_candidate(product_name):
    pn = product_name.lower()
    return '//' in pn or ('double' in pn and 'sided' in pn)


def get_market_price(manabox_row, ref_row=None):
    candidate_fields = ["TCG Marketplace Price", "List Price", "Retail Price"]
    if ref_row:
        for field in candidate_fields:
            price = str(ref_row.get(field, "")).strip()
            try:
                if price and float(price) > 0:
                    return price
            except ValueError:
                continue
    
    csv_candidate_fields = ["Purchase price"]
    for field in csv_candidate_fields:
        price = str(manabox_row.get(field, "")).strip()
        try:
            if price and float(price) > 0:
                return price
        except ValueError:
            continue
    
    return f"{FLOOR_PRICE:.2f}"


def normalize_key(card_name, set_name, condition, number):
    suffix = ""
    if "(" in card_name and ")" in card_name:
        card_name = re.sub(r"\(.*?\)", "", card_name).strip()
    
    card_name = remove_accents(card_name)
    card_name = card_name.split('//')[0].strip()
    normalized_card_name = re.sub(r"[^a-zA-Z0-9 ,'-]", "", card_name).strip().lower()
    
    set_name = remove_accents(set_name)
    normalized_set_name = re.sub(r"[^a-zA-Z0-9 ]", "", set_name).strip().lower()
    
    if normalized_set_name in ["plst", "the list"]:
        normalized_set_name = "the list reprints"
    
    if "prerelease cards" in normalized_set_name:
        return None
    
    if normalized_set_name == "the list":
        number = number.split("-")[-1] if number else ""
    
    normalized_number = re.sub(r"[^\d\-]", "", str(number).strip()) if number else None
    if normalized_number == "":
        normalized_number = None
    
    return normalized_card_name, normalized_set_name, normalized_number, condition.lower(), suffix


def find_best_match(normalized_key, card_database, ref_data):
    matches = []
    exact_number_matches = []
    
    for ref_key in card_database.keys():
        if normalized_key[0] and ref_key[0] and normalized_key[0][0] != ref_key[0][0]:
            continue
        
        query_words = normalized_key[0].split()
        candidate_words = ref_key[0].split()
        if len(query_words) == 1 and len(candidate_words) == 1:
            if query_words[0] != candidate_words[0]:
                continue
        elif len(query_words) > 1 and len(candidate_words) > 1:
            if not set(query_words).intersection(set(candidate_words)):
                continue
        
        base_score = fuzz.ratio(normalized_key[0], ref_key[0])
        if normalized_key[0] in ref_key[0] or ref_key[0] in normalized_key[0]:
            base_score += 20
        if normalized_key[1] == ref_key[1]:
            base_score += 50
        if not normalized_key[2] or not ref_key[2]:
            base_score += 50
        elif normalized_key[2] == ref_key[2]:
            base_score += 100
            exact_number_matches.append((ref_key, base_score))
        else:
            base_score -= 15
        
        cond1 = normalized_key[3].replace("foil", "").strip()
        cond2 = ref_key[3].replace("foil", "").strip()
        if cond1 in condition_rank and cond2 in condition_rank:
            diff = abs(condition_rank[cond1] - condition_rank[cond2])
            if diff == 0:
                base_score += 50
            elif diff == 1:
                base_score -= 10
            else:
                base_score -= 30
        else:
            if normalized_key[3] != ref_key[3]:
                base_score -= 20
        
        if ("prerelease" in ref_data[ref_key]["Product Name"].lower() or
                "prerelease cards" in ref_data[ref_key]["Set Name"].lower()):
            continue
        
        for term, penalty in SPECIAL_PRINT_PENALTIES.items():
            in_query = term in normalized_key[3]
            in_ref = term in ref_key[3]
            if in_query != in_ref:
                base_score -= penalty
        
        matches.append((ref_key, base_score))
    
    if exact_number_matches:
        matches = exact_number_matches
    elif matches and normalized_key[2]:
        print(
            f"Warning: No exact collector number match found for {normalized_key[0]} #{normalized_key[2]}. Showing closest variants.")
    
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def enhance_matches_with_scryfall(normalized_key, matches, ref_data, manabox_row=None):
    card_name, set_name, collector_number, condition, suffix = normalized_key
    scryfall_card = None
    
    if manabox_row and manabox_row.get("Scryfall ID"):
        scryfall_id = manabox_row.get("Scryfall ID").strip()
        if scryfall_id:
            scryfall_card = query_scryfall_by_id(scryfall_id)
    
    if not scryfall_card:
        set_code = SET_ALIAS.get(set_name, set_name)
        if len(set_name) > 3:
            words = set_name.split()
            if len(words) >= 2:
                set_code = ''.join(word[0] for word in words[:3]).lower()
        
        scryfall_card = query_scryfall_card(card_name, set_code, collector_number)
    
    if scryfall_card:
        if not matches or (matches and matches[0][1] < 300):
            promo_info = ""
            if scryfall_card.get('promo'):
                promo_types = scryfall_card.get('promo_types', [])
                promo_info = f" (Promo: {', '.join(promo_types)})" if promo_types else " (Promo)"
            
            if manabox_row:
                scryfall_entry = create_scryfall_fallback_entry(scryfall_card, manabox_row, condition)
                synthetic_key = (card_name, set_name, collector_number, condition, suffix)
                synthetic_match = (synthetic_key, 350)
                ref_data[synthetic_key] = scryfall_entry
                matches.insert(0, synthetic_match)
                print(f"Found Scryfall-only variant{promo_info}")
    else:
        print(f"Card not found on Scryfall")
    
    return matches


def create_scryfall_fallback_entry(scryfall_card, manabox_row, condition):
    promo_suffix = ""
    if scryfall_card.get('promo'):
        promo_types = scryfall_card.get('promo_types', [])
        if promo_types:
            promo_suffix = f" ({', '.join(promo_types).title()})"
    
    return {
        "TCGplayer Id": "Scryfall Verified",
        "Product Line": "Magic: The Gathering",
        "Set Name": scryfall_card.get('set_name', ''),
        "Product Name": scryfall_card.get('name', '') + promo_suffix,
        "Number": scryfall_card.get('collector_number', ''),
        "Rarity": scryfall_card.get('rarity', '').title(),
        "Condition": condition,
        "Add to Quantity": int(manabox_row.get("Quantity", "1")),
        "TCG Marketplace Price": get_market_price(manabox_row, None)
    }


def merge_entries(cards):
    merged = {}
    for card in cards:
        key = (card['TCGplayer Id'], card['Condition'])
        if key in merged:
            merged[key]['Add to Quantity'] += card['Add to Quantity']
        else:
            merged[key] = card
    return list(merged.values())


def auto_confirm_high_score(cards):
    confirmed = []
    for card in cards:
        if card.get('Score', 0) >= 250:
            confirmed.append(card)
    return confirmed
