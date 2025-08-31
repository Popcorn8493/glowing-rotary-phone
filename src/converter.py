import csv
from tkinter import Tk
from .config import TCGPLAYER_FIELDS
from .file_handling import (
    detect_csv_files, load_reference_data, create_output_folder, write_output_files
)
from .card_processing import (
    map_fields, get_pending_confirmations, clear_pending_confirmations,
    get_given_up_cards, get_scryfall_only_cards, get_confirmed_matches
)
from .data_processing import merge_entries
from .gui import confirm_match_gui_batch, select_csv_file


def process_confirmations():
    pending_confirmations = get_pending_confirmations()
    
    if not pending_confirmations:
        return
    
    print(f"\nProcessing {len(pending_confirmations)} manual confirmations...")
    
    try:
        confirmation_results = confirm_match_gui_batch(pending_confirmations)
        confirmed_count = 0
        skipped_count = 0
        
        for i, result in confirmation_results.items():
            if i < len(pending_confirmations):
                normalized_key, matches, ref_data = pending_confirmations[i]
                
                if result:
                    confirmed_matches = get_confirmed_matches()
                    confirmed_matches[normalized_key] = result
                    ref_row = ref_data[result]
                    confirmed_count += 1
                    print(f"Confirmed: {normalized_key[0]} -> {ref_row.get('Product Name', 'Unknown')}")
                else:
                    skipped_count += 1
                    print(f"Skipped: {normalized_key[0]}")
        
        print(f"Manual confirmations completed: {confirmed_count} confirmed, {skipped_count} skipped")
        clear_pending_confirmations()
    
    except Exception as e:
        print(f"GUI confirmation failed: {e}")
        print("Adding all unconfirmed items to unmatched list...")
        for normalized_key, matches, ref_data in pending_confirmations:
            print(f"Unmatched: {normalized_key[0]}")
        clear_pending_confirmations()


def convert_manabox_to_tcgplayer(manabox_csv, reference_csv):
    print("MTG Card Converter v2.0")
    print("Starting conversion process...")
    
    ref_data = load_reference_data(reference_csv)
    
    output_dir = create_output_folder()
    print(f"Output folder: {output_dir}")
    
    cards = []
    try:
        with open(manabox_csv, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                tcgplayer_row = map_fields(row, ref_data)
                if tcgplayer_row:
                    cards.append(tcgplayer_row)
        
        merged_cards = merge_entries(cards)
        print(f"Conversion complete: {len(merged_cards)} cards")
        
        process_confirmations()
        
        scryfall_only_cards = get_scryfall_only_cards()
        given_up_cards = get_given_up_cards()
        
        output_files = write_output_files(output_dir, merged_cards, scryfall_only_cards, given_up_cards)
        
        print(f"\nFiles saved to: {output_dir}")
        for file_path in output_files:
            file_name = file_path.split('/')[-1] if '/' in file_path else file_path
            print(f"  - {file_name}")
        
        if scryfall_only_cards:
            print(f"Missing from TCGplayer: {len(scryfall_only_cards)} cards")
        
        if given_up_cards:
            print(f"Unmatched: {len(given_up_cards)} cards")
        
        return output_dir, output_files
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise


def main():
    print("MTG Card Converter v2.0")
    print("Scanning for CSV files...")
    
    detected_manabox, detected_tcgplayer = detect_csv_files()
    
    if detected_manabox and detected_tcgplayer:
        print(f"Auto-detected files:")
        print(f"  Manabox CSV: {detected_manabox.name}")
        print(f"  TCGplayer CSV: {detected_tcgplayer.name}")
        manabox_csv = str(detected_manabox)
        reference_csv = str(detected_tcgplayer)
    else:
        print("Could not auto-detect both files. Please select manually...")
        Tk().withdraw()
        
        if not detected_manabox:
            manabox_csv = select_csv_file("Select the Manabox CSV File")
        else:
            print(f"Using detected Manabox file: {detected_manabox.name}")
            manabox_csv = str(detected_manabox)
        
        if not detected_tcgplayer:
            reference_csv = select_csv_file("Select the TCGPlayer Reference CSV File")
        else:
            print(f"Using detected TCGplayer file: {detected_tcgplayer.name}")
            reference_csv = str(detected_tcgplayer)
    
    try:
        output_dir, output_files = convert_manabox_to_tcgplayer(manabox_csv, reference_csv)
        print(f"\nConversion completed successfully!")
        return output_dir, output_files
    except Exception as e:
        print(f"Conversion failed: {e}")
        return None, None


if __name__ == "__main__":
    main()
