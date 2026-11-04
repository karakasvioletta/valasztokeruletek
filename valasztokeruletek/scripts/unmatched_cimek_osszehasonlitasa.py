import sys
import re
import unicodedata
from pathlib import Path

import pandas as pd


# ==================================================
# 1. ÚTVONALAK ÉS BEÁLLÍTÁSOK
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import PROCESSED_DATA_DIR


INPUT_2022 = PROCESSED_DATA_DIR / "csak_2022_cimek.csv"
INPUT_2026 = PROCESSED_DATA_DIR / "csak_2026_cimek.csv"

OUTPUT_DIR = PROCESSED_DATA_DIR / "comparison"


# ==================================================
# 2. SZÖVEGEK NORMALIZÁLÁSA
# ==================================================

def normalize_text(value):
    """
    Egységesíti a szöveges értékeket:
    - kisbetűssé alakítja;
    - eltávolítja az ékezeteket;
    - egységesíti a szóközöket;
    - eltávolítja a felesleges írásjeleket.
    """

    if pd.isna(value):
        return ""

    value = str(value).lower().strip()

    # Ékezetek eltávolítása
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    # Írásjelek helyettesítése szóközzel
    value = re.sub(r"[.,;:]", " ", value)

    # Többszörös szóközök eltávolítása
    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ==================================================
# 3. KÖZTERÜLET-JELLEGEK EGYSÉGESÍTÉSE
# ==================================================

STREET_TYPE_MAP = {
    "u": "utca",
    "u.": "utca",
    "utca": "utca",

    "krt": "korut",
    "krt.": "korut",
    "korut": "korut",

    "ter": "ter",
    "ts": "ter",
}


def normalize_street_type(value):
    value = normalize_text(value)

    return STREET_TYPE_MAP.get(value, value)


# ==================================================
# 4. HÁZSZÁMOK NORMALIZÁLÁSA
# ==================================================

def normalize_house_number(value):
    """
    Egységesíti a házszámok formázását.

    Példák:
    12.     -> 12
    12 / A  -> 12/a
    0012    -> 12
    """

    if pd.isna(value):
        return ""

    value = str(value).lower().strip()

    # Szóközök eltávolítása
    value = re.sub(r"\s+", "", value)

    # Záró pont eltávolítása
    value = value.rstrip(".")

    # Egyszerű, csak számból álló házszámok kezelése
    if value.isdigit():
        value = str(int(value))

    return value


# ==================================================
# 5. ADATOK NORMALIZÁLÁSA
# ==================================================

def prepare_data(df, year):
    """
    Létrehozza a normalizált oszlopokat.
    Az eredeti oszlopokat változatlanul hagyja.
    """

    df = df.copy()

    df["közterület_neve_norm"] = (
        df["közterület_neve"].apply(normalize_text)
    )

    df["közterület_jellege_norm"] = (
        df["közterület_jellege"].apply(normalize_street_type)
    )

    df["házszám_norm"] = (
        df["házszám"].apply(normalize_house_number)
    )

    df["épület_norm"] = (
        df["épület"].apply(normalize_text)
    )

    df["lépcsőház_norm"] = (
        df["lépcsőház"].apply(normalize_text)
    )

    # Egyedi sorszám a forrásrekordok azonosításához
    df["_record_id"] = range(len(df))

    return df


# ==================================================
# 6. EGYÉRTELMŰ EGYEZÉSEK KERESÉSE
# ==================================================

def find_unique_matches(df22, df26, keys, method):
    """
    Csak azokat a kulcsokat párosítja,
    amelyek mindkét adatbázisban pontosan egyszer szerepelnek.

    Így elkerüljük, hogy egy címhez több lehetséges
    másik címet automatikusan hozzárendeljünk.
    """

    # Kulcsok előfordulásának megszámolása
    count22 = (
        df22.groupby(keys, dropna=False)
        .size()
        .reset_index(name="_count_22")
    )

    count26 = (
        df26.groupby(keys, dropna=False)
        .size()
        .reset_index(name="_count_26")
    )

    # Csak azok a kulcsok maradnak,
    # amelyek mindkét adatbázisban egyszer szerepelnek
    unique_keys = count22.merge(
        count26,
        on=keys,
        how="inner",
    )

    unique_keys = unique_keys[
        (unique_keys["_count_22"] == 1)
        & (unique_keys["_count_26"] == 1)
    ][keys]

    # A megfelelő rekordok kiválasztása
    matches22 = df22.merge(
        unique_keys,
        on=keys,
        how="inner",
    )

    matches26 = df26.merge(
        unique_keys,
        on=keys,
        how="inner",
    )

    # A két oldal párosítása
    matches = matches22.merge(
        matches26,
        on=keys,
        how="inner",
        suffixes=("_22", "_26"),
    )

    matches["egyeztetesi_modszer"] = method

    return matches


# ==================================================
# 7. FŐ FELDOLGOZÁSI FOLYAMAT
# ==================================================

def build(adat22=None, adat26=None):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nÖsszehasonlítás indítása...")

    # CSV-k beolvasása, ha nem kaptunk DataFrame-et
    if adat22 is None:
        print("2022-es címek beolvasása...")
        adat22 = pd.read_csv(
            INPUT_2022,
            dtype=str,
            encoding="utf-8-sig",
        )

    if adat26 is None:
        print("2026-os címek beolvasása...")
        adat26 = pd.read_csv(
            INPUT_2026,
            dtype=str,
            encoding="utf-8-sig",
        )

    print(f"2022-es címek: {len(adat22):,}")
    print(f"2026-os címek: {len(adat26):,}")

    # Normalizálás
    print("\nCímek normalizálása...")

    adat22 = prepare_data(adat22, 2022)
    adat26 = prepare_data(adat26, 2026)

    # ==================================================
    # 7/A. ELSŐ SZINT: TELJES NORMALIZÁLT EGYEZÉS
    # ==================================================

    print("\n1. Teljes normalizált egyezések keresése...")

    teljes_kulcsok = [
        "település_azonosító",
        "közterület_neve_norm",
        "közterület_jellege_norm",
        "házszám_norm",
        "épület_norm",
        "lépcsőház_norm",
    ]

    egyezes_1 = find_unique_matches(
        adat22,
        adat26,
        teljes_kulcsok,
        "teljes_normalizalt_egyezes",
    )

    # Már párosított rekordok azonosítói
    parositott_22 = set(egyezes_1["_record_id_22"])
    parositott_26 = set(egyezes_1["_record_id_26"])

    maradek_22 = adat22[
        ~adat22["_record_id"].isin(parositott_22)
    ].copy()

    maradek_26 = adat26[
        ~adat26["_record_id"].isin(parositott_26)
    ].copy()

    print(f"Talált egyezések: {len(egyezes_1):,}")

    # ==================================================
    # 7/B. MÁSODIK SZINT: EGYSZERŰSÍTETT EGYEZÉS
    # ==================================================

    print("\n2. Egyszerűsített kulcsok alapján történő keresés...")

    egyszerusitett_kulcsok = [
        "település_azonosító",
        "közterület_neve_norm",
        "házszám_norm"
    ]

    egyezes_2 = find_unique_matches(
        maradek_22,
        maradek_26,
        egyszerusitett_kulcsok,
        "egyszerusitett_egyezes",
    )

    print(f"Talált további egyezések: {len(egyezes_2):,}")

    # ==================================================
    # 8. EGYEZÉSEK ÖSSZEFŰZÉSE
    # ==================================================

    print("\nEredmények összesítése...")

    egyezesek = pd.concat(
        [egyezes_1, egyezes_2],
        ignore_index=True,
    )

    # ==================================================
    # 9. EREDMÉNYEK MENTÉSE
    # ==================================================

    egyezesek.to_csv(
        OUTPUT_DIR / "normalizalt_egyezesek.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # A már párosított rekordok eltávolítása
    osszes_parositott_22 = (
        parositott_22
        | set(egyezes_2["_record_id_22"])
    )

    osszes_parositott_26 = (
        parositott_26
        | set(egyezes_2["_record_id_26"])
    )

    nem_parosithato_22 = adat22[
        ~adat22["_record_id"].isin(osszes_parositott_22)
    ].copy()

    nem_parosithato_26 = adat26[
        ~adat26["_record_id"].isin(osszes_parositott_26)
    ].copy()

    # Segédoszlopok eltávolítása
    segedoszlopok = [
        "_record_id",
        "közterület_neve_norm",
        "közterület_jellege_norm",
        "házszám_norm",
        "épület_norm",
        "lépcsőház_norm",
    ]

    nem_parosithato_22 = nem_parosithato_22.drop(
        columns=segedoszlopok,
        errors="ignore",
    )

    nem_parosithato_26 = nem_parosithato_26.drop(
        columns=segedoszlopok,
        errors="ignore",
    )

    nem_parosithato_22.to_csv(
        OUTPUT_DIR / "nem_parosithato_2022.csv",
        index=False,
        encoding="utf-8-sig",
    )

    nem_parosithato_26.to_csv(
        OUTPUT_DIR / "nem_parosithato_2026.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # ==================================================
    # 10. ÖSSZESÍTÉS
    # ==================================================

    print("\n====================================")
    print("ÖSSZEHASONLÍTÁS EREDMÉNYE")
    print("====================================")

    print(f"Teljes normalizált egyezés: {len(egyezes_1):,}")
    print(f"Egyszerűsített egyezés: {len(egyezes_2):,}")
    print(f"Összes új egyezés: {len(egyezesek):,}")

    print(f"\nPárosítatlan 2022-es címek: {len(nem_parosithato_22):,}")
    print(f"Párosítatlan 2026-os címek: {len(nem_parosithato_26):,}")

    print(f"\nEredmények mentési helye: {OUTPUT_DIR}")


# ==================================================
# 11. ÖNÁLLÓ FUTTATÁS
# ==================================================

if __name__ == "__main__":
    build()