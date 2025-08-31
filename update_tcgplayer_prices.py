import argparse
import sys
from typing import Any
import pandas as pd
import numpy as np
from pathlib import Path
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from numpy import ndarray, dtype

FLOOR_PRICE = 0.25


def load_csv(path: Path) -> pd.DataFrame:
    """Load inventory CSV into a DataFrame."""
    return pd.read_csv(path)


def calculate_prices(df: pd.DataFrame) -> pd.Series:
    """
    Calculate 'TCG Marketplace Price' with dynamic multipliers, Example:
      - $1 <= base price < $15: 150% of base
      - base price >= $15:      130% of base
      - otherwise (below $1):   150% of base
    Enforce a minimum price floor.
    """

    base = df['TCG Market Price'].fillna(df['TCG Low Price'].fillna(0.0))

    price = pd.Series(index=base.index, dtype=float)


    mask_1_15 = (base >= 1.0) & (base < 15.0)
    mask_ge15 = base >= 15.0
    mask_other = ~(mask_1_15 | mask_ge15)

    price[mask_1_15] = base[mask_1_15] * 1.5
    price[mask_ge15] = base[mask_ge15] * 1.3
    price[mask_other] = base[mask_other] * 1.5

    return price.clip(lower=FLOOR_PRICE)


def update_quantities(df: pd.DataFrame) -> ndarray[tuple[Any, ...], dtype[Any]]:
    """
    Update 'Total Quantity' by adding 'Add to Quantity',
    but never drop below the original 'Total Quantity'.
    """
    current = df['Total Quantity'].fillna(0).astype(int)
    add = df.get('Add to Quantity', pd.Series(0, index=df.index)).fillna(0).astype(int)

    total = current + add
    return np.where(total >= current, total, current)


def main():
    parser = argparse.ArgumentParser(description="Update TCGPlayer inventory CSV.")
    parser.add_argument('input', nargs='?', help="Input CSV file path")
    parser.add_argument('-o', '--output', help="Output CSV file path",
                        default='Updated_TCGplayer_Inventory.csv')
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else None
    if not input_path or not input_path.exists():
        Tk().withdraw()  
        chosen = askopenfilename(
            title="Select the input CSV file",
            filetypes=[("CSV files", "*.csv")]
        )
        if not chosen:
            print("No file selected. Exiting...")
            sys.exit(1)
        input_path = Path(chosen)

    df = load_csv(input_path)
    df['TCG Marketplace Price'] = calculate_prices(df)
    df['Total Quantity'] = update_quantities(df)
    df.to_csv(args.output, index=False)
    print(f"Updated inventory saved to {args.output}")


if __name__ == "__main__":
    main()
