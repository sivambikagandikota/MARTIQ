# MARTIQ — Smart Supermarket Management & Intelligence System

A supermarket management, billing (POS), analytics, and smart inventory
recommendation system built with Python, Streamlit, SQLite, and Pandas.

## Status: Phase 1 of 10 (Project Structure + Database)

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
streamlit run app.py
```

The SQLite database (`database/martiq.db`) is created automatically the
first time the app runs — no manual setup needed.

## Demo Login

- Username: `admin`
- Password: `martiq123`

(Login screen itself arrives in Phase 2.)

## Tech Stack

- Python + Streamlit (UI)
- SQLite (database)
- Pandas (data handling)
- Plotly / Matplotlib (charts)

## Project Structure

```
MARTIQ/
├── app.py                 Main entry point
├── database.py            All SQL / database logic
├── config.py               Settings, theme, constants
├── requirements.txt
├── views/                  One file per app module (named "views", not
│                           "pages", so Streamlit doesn't auto-generate
│                           its own multipage navigation from it)
├── database/martiq.db      Auto-created SQLite file
├── utils/                  Shared helper logic
└── assets/                 Logo/images
```


## Added Integrated Features
- Dataset Analysis page with bundled SuperMarket Analysis.csv, CSV/XLSX upload, Pandas cleaning, analysis, charts, and business insights.
- Product and customer bulk upload with CSV/XLSX templates and duplicate validation.
- Barcode-ready products: each product has a barcode; blank barcodes receive a MARTIQ-generated code.
- Billing barcode scanner input for USB/keyboard barcode scanners and optional camera/image barcode detection.
- Barcode lookup adds the matching product directly to the current billing cart.

Run from the MARTIQ folder:
`\.\venv\Scripts\python.exe -m streamlit run app.py`
