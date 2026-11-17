
from pathlib import Path

# A projekt gyökérmappája
PROJECT_DIR = Path(__file__).resolve().parent

# Adatok mappái
DATA_DIR = PROJECT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REFERENCE_TABLES_DIR = PROCESSED_DATA_DIR / "reference_tables"
COMPARISON_DIR = PROCESSED_DATA_DIR / "comparison"
DIFFERENCES_DIR = PROCESSED_DATA_DIR / "differences"
MATCHES_DIR = PROCESSED_DATA_DIR / "matches"


# Forrásfájlok
FILE_2022 = RAW_DATA_DIR / "2022_korzetadatok.csv"
FILE_2026 = RAW_DATA_DIR / "2026_korzetadatok.csv"

# Kimeneti fájlok
SZAVAZOKOROK_2022 = PROCESSED_DATA_DIR / "szavazokorok_2022.csv"
SZAVAZOKOROK_2026 = PROCESSED_DATA_DIR / "szavazokorok_2026.csv"
MEGYEK_FILE = PROCESSED_DATA_DIR / "megyek.csv"
TELEPULESEK_FILE = PROCESSED_DATA_DIR / "telepulesek.csv"
EGYEZO_CIMEK_FILE = PROCESSED_DATA_DIR / "egyezo_cimek_22_26.csv"
