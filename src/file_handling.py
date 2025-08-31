import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from .config import FILTER_PRERELEASE, FILTER_PROMO, PROMO_PATTERNS, TCGPLAYER_FIELDS
from .data_processing import normalize_key


def detect_csv_files():
    current_dir = Path(".")
    csv_files = list(current_dir.glob("*.csv"))
    
    print(f"Found {len(csv_files)} CSV files to analyze...")
    
    manabox_file = None
    tcgplayer_file = None
    
    for csv_file in csv_files:
        filename_lower = csv_file.name.lower()
        print(f"Analyzing: {csv_file.name}")
        
        if any(skip in filename_lower for skip in
               ['tcgplayer_staged', 'scryfall_verified', 'tcgplayer_given_up', 'cards_missing_from_tcgplayer']):
            print(f"  Skipping output file")
            continue
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                header = f.readline().lower()
                manabox_indicators = ['manabox id', 'scryfall id', 'set code']
                manabox_matches = [col for col in manabox_indicators if col in header]
                tcgplayer_indicators = ['tcgplayer id', 'product line', 'tcg market price']
                tcgplayer_matches = [col for col in tcgplayer_indicators if col in header]
                
                print(f"  Manabox indicators found: {manabox_matches}")
                print(f"  TCGplayer indicators found: {tcgplayer_matches}")
                
                if 'manabox id' in header and 'scryfall id' in header:
                    if not manabox_file:
                        manabox_file = csv_file
                        print(f"  -> Identified as Manabox file")
                        continue
                
                if 'tcgplayer id' in header and 'product line' in header:
                    if not tcgplayer_file:
                        tcgplayer_file = csv_file
                        print(f"  -> Identified as TCGplayer file")
                        continue
                
                if 'set code' in header and 'collector number' in header and 'manabox id' not in header:
                    if not manabox_file and 'scryfall id' in header:
                        manabox_file = csv_file
                        print(f"  -> Identified as Manabox-like file")
                        continue
                
                print(f"  -> Could not identify file type")
        
        except Exception as e:
            print(f"  -> Error reading file: {e}")
            continue
    
    return manabox_file, tcgplayer_file


def load_reference_data(reference_csv):
    start_time = time.time()
    print("Loading reference database...")
    
    try:
        ref_df = pd.read_csv(reference_csv, dtype={"Number": "str"})
        original_count = len(ref_df)
        ref_df = ref_df[ref_df["Set Name"].notnull()]
        excluded_count = 0
        
        if FILTER_PRERELEASE:
            mask = ref_df["Product Name"].str.contains("Prerelease", case=False, na=False)
            excluded_count += mask.sum()
            ref_df = ref_df[~mask]
        
        if FILTER_PROMO:
            mask = ref_df["Product Name"].str.contains("|".join(PROMO_PATTERNS), case=False, na=False)
            excluded_count += mask.sum()
            ref_df = ref_df[~mask]
        
        records = ref_df.to_dict('records')
        ref_data = {}
        
        for row in records:
            key = normalize_key(
                row.get("Product Name", ""),
                row.get("Set Name", ""),
                row.get("Condition", "Near Mint"),
                row.get("Number", "")
            )
            if key:
                ref_data[key] = row
        
        total_time = time.time() - start_time
        print(f"Loaded {len(ref_data):,} cards in {total_time:.1f}s" +
              (f" (excluded {excluded_count:,})" if excluded_count > 0 else ""))
        
        return ref_data
    
    except FileNotFoundError:
        print(f"Reference file not found: {reference_csv}")
        exit()


def create_output_folder():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"converted_output_{timestamp}")
    output_dir.mkdir(exist_ok=True)
    return output_dir


def write_output_files(output_dir, merged_cards, scryfall_only_cards, given_up_cards):
    output_files = []
    
    tcgplayer_csv = output_dir / "tcgplayer_staged_inventory.csv"
    with open(tcgplayer_csv, mode='w', newline='', encoding='utf-8') as outfile:
        import csv
        writer = csv.DictWriter(outfile, fieldnames=TCGPLAYER_FIELDS)
        writer.writeheader()
        for card in merged_cards:
            writer.writerow(card)
    output_files.append(str(tcgplayer_csv))
    
    if scryfall_only_cards:
        scryfall_csv = output_dir / "cards_missing_from_tcgplayer.csv"
        with open(scryfall_csv, mode='w', newline='', encoding='utf-8') as sfile:
            import csv
            swriter = csv.DictWriter(sfile, fieldnames=TCGPLAYER_FIELDS)
            swriter.writeheader()
            for entry in scryfall_only_cards:
                swriter.writerow(entry)
        output_files.append(str(scryfall_csv))
        print(f"Missing from TCGplayer: {len(scryfall_only_cards)} cards")
    
    if given_up_cards:
        given_up_csv = output_dir / "tcgplayer_given_up.csv"
        with open(given_up_csv, mode='w', newline='', encoding='utf-8') as gfile:
            import csv
            gwriter = csv.DictWriter(gfile, fieldnames=TCGPLAYER_FIELDS)
            gwriter.writeheader()
            for entry in given_up_cards:
                gwriter.writerow(entry)
        output_files.append(str(given_up_csv))
        print(f"Unmatched: {len(given_up_cards)} cards")
    
    return output_files
