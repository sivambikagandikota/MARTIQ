"""
MARTIQ - Small Shared Helpers
--------------------------------
Currently just the CSV/Excel export helpers used by Reports. Kept
separate from ui.py (visual components) and validators.py (input
checks) since this is about data export, a different concern.
"""

import io

import pandas as pd


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Return CSV bytes for a download button."""
    return df.to_csv(index=False).encode("utf-8")


def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    """Return XLSX bytes for a download button (uses openpyxl)."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()
