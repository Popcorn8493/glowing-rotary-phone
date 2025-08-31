import time
import requests
import json
from typing import List, Dict, Optional, Any
from .config import SCRYFALL_API_BASE, SCRYFALL_RATE_LIMIT

last_scryfall_request = 0
scryfall_cache = {}
current_rate_limit = SCRYFALL_RATE_LIMIT
consecutive_429s = 0
last_429_time = 0


def adaptive_rate_limit():
    global last_scryfall_request, current_rate_limit, consecutive_429s, last_429_time
    
    current_time = time.time()
    elapsed = current_time - last_scryfall_request
    
    if consecutive_429s > 0 and current_time - last_429_time < 60:
        backoff_multiplier = min(2 ** consecutive_429s, 8)
        effective_limit = current_rate_limit * backoff_multiplier
    else:
        consecutive_429s = 0
        effective_limit = current_rate_limit
    
    if elapsed < effective_limit:
        sleep_time = effective_limit - elapsed
        time.sleep(sleep_time)
    
    last_scryfall_request = time.time()


def handle_rate_limit_response(response: requests.Response) -> None:
    global consecutive_429s, last_429_time, current_rate_limit
    
    if response.status_code == 429:
        consecutive_429s += 1
        last_429_time = time.time()
        
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                wait_time = int(retry_after)
                print(f"Rate limited - waiting {wait_time} seconds")
                time.sleep(wait_time)
            except ValueError:
                time.sleep(5)
        else:
            wait_time = min(2 ** consecutive_429s, 30)
            print(f"Rate limited - waiting {wait_time} seconds")
            time.sleep(wait_time)
    else:
        if consecutive_429s == 0 and current_rate_limit > SCRYFALL_RATE_LIMIT:
            current_rate_limit = max(current_rate_limit * 0.9, SCRYFALL_RATE_LIMIT)


def batch_query_scryfall_collection(identifiers: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not identifiers or len(identifiers) == 0:
        return {'data': [], 'not_found': []}
    
    if len(identifiers) > 75:
        raise ValueError("Maximum 75 identifiers allowed per batch request")
    
    cache_key = f"batch|{hash(json.dumps(identifiers, sort_keys=True))}"
    if cache_key in scryfall_cache:
        return scryfall_cache[cache_key]
    
    adaptive_rate_limit()
    
    try:
        url = f"{SCRYFALL_API_BASE}/cards/collection"
        headers = {'Content-Type': 'application/json'}
        payload = {'identifiers': identifiers}
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        handle_rate_limit_response(response)
        
        if response.status_code == 200:
            result = response.json()
            scryfall_cache[cache_key] = result
            return result
        else:
            print(f"Batch query failed with status {response.status_code}")
            return {'data': [], 'not_found': identifiers}
    
    except Exception as e:
        print(f"Batch query error: {e}")
        return {'data': [], 'not_found': identifiers}


def query_scryfall_card(card_name, set_code, collector_number=None):
    cache_key = f"{card_name}|{set_code}|{collector_number or ''}"
    
    if cache_key in scryfall_cache:
        return scryfall_cache[cache_key]
    
    adaptive_rate_limit()
    
    try:
        if collector_number:
            url = f"{SCRYFALL_API_BASE}/cards/{set_code}/{collector_number}"
            response = requests.get(url, timeout=10)
            handle_rate_limit_response(response)
            
            if response.status_code == 200:
                card_data = response.json()
                scryfall_cache[cache_key] = card_data
                return card_data
        
        params = {
            'q': f'"{card_name}" set:{set_code}',
            'format': 'json'
        }
        url = f"{SCRYFALL_API_BASE}/cards/search"
        response = requests.get(url, params=params, timeout=10)
        handle_rate_limit_response(response)
        
        if response.status_code == 200:
            search_data = response.json()
            if search_data.get('total_cards', 0) > 0:
                for card in search_data.get('data', []):
                    if card.get('name', '').lower() == card_name.lower():
                        scryfall_cache[cache_key] = card
                        return card
                first_card = search_data['data'][0]
                scryfall_cache[cache_key] = first_card
                return first_card
        
        scryfall_cache[cache_key] = None
        return None
    
    except Exception as e:
        print(f"Scryfall API error for {card_name} ({set_code}): {e}")
        scryfall_cache[cache_key] = None
        return None


def get_scryfall_variants(card_name, set_code):
    cache_key = f"variants|{card_name}|{set_code}"
    
    if cache_key in scryfall_cache:
        return scryfall_cache[cache_key]
    
    adaptive_rate_limit()
    
    try:
        params = {
            'q': f'"{card_name}" set:{set_code}',
            'format': 'json'
        }
        url = f"{SCRYFALL_API_BASE}/cards/search"
        response = requests.get(url, params=params, timeout=10)
        handle_rate_limit_response(response)
        
        if response.status_code == 200:
            search_data = response.json()
            variants = []
            for card in search_data.get('data', []):
                if card.get('name', '').lower() == card_name.lower():
                    variant_info = {
                        'collector_number': card.get('collector_number'),
                        'promo': card.get('promo', False),
                        'promo_types': card.get('promo_types', []),
                        'frame_effects': card.get('frame_effects', []),
                        'finishes': card.get('finishes', []),
                        'variation': card.get('variation', False),
                        'full_art': card.get('full_art', False),
                        'textless': card.get('textless', False),
                        'image_status': card.get('image_status'),
                        'border_color': card.get('border_color')
                    }
                    variants.append(variant_info)
            
            scryfall_cache[cache_key] = variants
            return variants
        
        scryfall_cache[cache_key] = []
        return []
    
    except Exception as e:
        print(f"Scryfall variants error for {card_name} ({set_code}): {e}")
        scryfall_cache[cache_key] = []
        return []


def query_scryfall_by_id(scryfall_id):
    cache_key = f"id|{scryfall_id}"
    
    if cache_key in scryfall_cache:
        return scryfall_cache[cache_key]
    
    adaptive_rate_limit()
    
    try:
        url = f"{SCRYFALL_API_BASE}/cards/{scryfall_id}"
        response = requests.get(url, timeout=10)
        handle_rate_limit_response(response)
        
        if response.status_code == 200:
            card_data = response.json()
            scryfall_cache[cache_key] = card_data
            return card_data
        
        scryfall_cache[cache_key] = None
        return None
    
    except Exception as e:
        print(f"Scryfall ID query error for {scryfall_id}: {e}")
        scryfall_cache[cache_key] = None
        return None


def clear_cache():
    global scryfall_cache
    scryfall_cache.clear()


def batch_process_cards(cards_data: List[Dict[str, str]], batch_size: int = 75) -> List[Dict[str, Any]]:
    """
    Process multiple cards using batching for efficiency.
    
    Args:
        cards_data: List of card data dicts with 'name', 'set_code', etc.
        batch_size: Number of cards per batch (max 75)
    
    Returns:
        List of Scryfall card data
    """
    results = []
    
    for i in range(0, len(cards_data), batch_size):
        batch = cards_data[i:i + batch_size]
        
        # Convert card data to identifiers format
        identifiers = []
        for card in batch:
            identifier = {'name': card.get('name', '')}
            if card.get('set_code'):
                identifier['set'] = card['set_code'].lower()
            if card.get('collector_number'):
                identifier['collector_number'] = card['collector_number']
            identifiers.append(identifier)
        
        print(f"Processing batch {i // batch_size + 1} ({len(identifiers)} cards)")
        batch_result = batch_query_scryfall_collection(identifiers)
        
        # Add found cards to results
        for card in batch_result.get('data', []):
            results.append(card)
        
        # Handle not found cards
        if batch_result.get('not_found'):
            print(f"  {len(batch_result['not_found'])} cards not found in this batch")
    
    return results


def get_cache_stats():
    return {
        'cache_size': len(scryfall_cache),
        'rate_limit': current_rate_limit,
        'consecutive_429s': consecutive_429s,
        'last_429_time': last_429_time,
        'time_since_last_429': time.time() - last_429_time if last_429_time > 0 else None
    }
