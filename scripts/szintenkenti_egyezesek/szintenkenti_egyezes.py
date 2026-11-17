
import sys
import re
import unicodedata
import time
from pathlib import Path
from collections import Counter

import pandas as pd


# ==================================================
# 1. ÚTVONALAK ÉS BEÁLLÍTÁSOK
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from config import PROCESSED_DATA_DIR

INPUT_DIR = PROCESSED_DATA_DIR / "comparison"

FILE_22 = INPUT_DIR / "nem_parosithato_2022.csv"
FILE_26 = INPUT_DIR / "nem_parosithato_2026.csv"

OUTPUT_DIR = INPUT_DIR / "level_matches"


# ==================================================
# 2. NORMALIZÁLÁS
# ==================================================

def normalize_text(value):

    if pd.isna(value) or str(value).strip() == "":
        return ""

    value = str(value).lower()
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("utf-8")
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_house_number(value):

    value = normalize_text(value)

    if value.isdigit():
        value = str(int(value))

    return value


def normalize_street_type(value):

    value = normalize_text(value)

    street_type_map = {
        "u": "utca",
        "utca": "utca",
        "ut": "ut",
        "korut": "korut",
        "krt": "korut",
        "ter": "ter",
        "ts": "ter",
    }

    return street_type_map.get(value, value)


NORMALIZATION = {
    "település_azonosító": normalize_text,
    "közterület_neve": normalize_text,
    "közterület_jellege": normalize_street_type,
    "házszám": normalize_house_number,
    "épület": normalize_text,
    "lépcsőház": normalize_text,
}


def prepare_data(df):

    df = df.copy().reset_index(drop=True)

    df["_record_id"] = range(len(df))

    for col, func in NORMALIZATION.items():

        if col not in df.columns:
            raise ValueError(f"Hiányzó oszlop: {col}")

        df[col + "_norm"] = df[col].apply(func)

    return df


# ==================================================
# 3. EGYEZÉSI SZINTEK
# ==================================================

LEVELS = [
    {
        "name": "01_jelleg_nelkul",
        "description": "Közterület jellege eltérhet",
        "keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "házszám_norm",
            "épület_norm",
            "lépcsőház_norm",
        ],
        "required_keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "házszám_norm",
        ],
        "must_differ": ["közterület_jellege_norm"],
    },
    {
        "name": "02_lepcsohaz_nelkul",
        "description": "Lépcsőház eltérhet",
        "keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
            "házszám_norm",
            "épület_norm",
        ],
        "required_keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
            "házszám_norm",
        ],
        "must_differ": ["lépcsőház_norm"],
    },
    {
        "name": "03_epulet_nelkul",
        "description": "Épület eltérhet",
        "keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
            "házszám_norm",
            "lépcsőház_norm",
        ],
        "required_keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
            "házszám_norm",
        ],
        "must_differ": ["épület_norm"],
    },
    {
        "name": "04_hazszam_nelkul",
        "description": "Házszám eltérhet",
        "keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
            "épület_norm",
            "lépcsőház_norm",
        ],
        "required_keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
        ],
        "at_least_one": [
            "épület_norm",
            "lépcsőház_norm",
        ],
        "must_differ": ["házszám_norm"],
    },
    {
        "name": "05_epulet_lepcsohaz_nelkul",
        "description": "Épület és lépcsőház eltérhet",
        "keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
            "házszám_norm",
        ],
        "required_keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
            "házszám_norm",
        ],
        "must_differ": [
            "épület_norm",
            "lépcsőház_norm",
        ],
    },
    {
        "name": "06_hazszam_epulet_lepcsohaz_nelkul",
        "description": "Házszám, épület és lépcsőház eltérhet",
        "keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
        ],
        "required_keys": [
            "település_azonosító_norm",
            "közterület_neve_norm",
            "közterület_jellege_norm",
        ],
        "must_differ": [
            "házszám_norm",
            "épület_norm",
            "lépcsőház_norm",
        ],
    },
]


# ==================================================
# 4. KULCSOK ÉRVÉNYESSÉGÉNEK ELLENŐRZÉSE
# ==================================================

def is_valid_key(key, keys, required_fields, at_least_one=None):

    values = dict(zip(keys, key))

    if any(values[field] == "" for field in required_fields):
        return False

    if at_least_one and not any(
        values[field] != "" for field in at_least_one
    ):
        return False

    return True


# ==================================================
# 5. KÜLÖNBSÉGEK MEGHATÁROZÁSA
# ==================================================

DIFFERENCE_FIELDS = {
    "közterület_jellege": "közterület_jellege_norm",
    "házszám": "házszám_norm",
    "épület": "épület_norm",
    "lépcsőház": "lépcsőház_norm",
}


def get_differences(row22, row26):

    differences = []

    for original_col, norm_col in DIFFERENCE_FIELDS.items():

        if row22[norm_col] != row26[norm_col]:
            differences.append(original_col)

    return "; ".join(differences) if differences else "nincs"


# ==================================================
# 6. KIMENETI OSZLOPOK ÉS SOROK
# ==================================================

OUTPUT_COLUMNS = [
    "település_azonosító",
    "közterület_neve_22",
    "közterület_neve_26",
    "közterület_jellege_22",
    "közterület_jellege_26",
    "házszám_22",
    "házszám_26",
    "épület_22",
    "épület_26",
    "lépcsőház_22",
    "lépcsőház_26",
    "egyezesi_szint",
    "kulonbsegek",
]


def create_match_row(row22, row26, level_name):

    return {
        "település_azonosító": row22["település_azonosító"],
        "közterület_neve_22": row22["közterület_neve"],
        "közterület_neve_26": row26["közterület_neve"],
        "közterület_jellege_22": row22["közterület_jellege"],
        "közterület_jellege_26": row26["közterület_jellege"],
        "házszám_22": row22["házszám"],
        "házszám_26": row26["házszám"],
        "épület_22": row22["épület"],
        "épület_26": row26["épület"],
        "lépcsőház_22": row22["lépcsőház"],
        "lépcsőház_26": row26["lépcsőház"],
        "egyezesi_szint": level_name,
        "kulonbsegek": get_differences(row22, row26),
    }


# ==================================================
# 7. SZINTENKÉNTI EGYEZTETÉS
# ==================================================

def match_by_levels(adat22, adat26):

    maradek_22 = adat22.copy()
    maradek_26 = adat26.copy()

    tobbszoros_kulcsok = []
    ketertelmu_cimek = []

    for level in LEVELS:

        start_time = time.time()

        level_name = level["name"]
        keys = level["keys"]

        print("\n====================================")
        print(f"Egyezési szint: {level_name}")
        print("====================================")

        # Kulcsok előállítása az aktuális maradék adatokból.
        kulcsok_22 = list(
            zip(*(maradek_22[col] for col in keys))
        )

        kulcsok_26 = list(
            zip(*(maradek_26[col] for col in keys))
        )

        counts_22 = Counter(kulcsok_22)
        counts_26 = Counter(kulcsok_26)

        kozos_kulcsok = set(counts_22) & set(counts_26)

        required_fields = level["required_keys"]
        at_least_one = level.get("at_least_one")

        ervenyes_kulcsok = {
            key
            for key in kozos_kulcsok
            if is_valid_key(
                key,
                keys,
                required_fields,
                at_least_one,
            )
        }

        egyedi_kulcsok = {
            key
            for key in ervenyes_kulcsok
            if counts_22[key] == 1 and counts_26[key] == 1
        }

        ambig_kulcsok = {
            key
            for key in ervenyes_kulcsok
            if counts_22[key] > 1 or counts_26[key] > 1
        }

        # Az egyedi kulcsok rekordindexei.
        lookup_22 = {
            key: index
            for index, key in enumerate(kulcsok_22)
            if key in egyedi_kulcsok
        }

        lookup_26 = {
            key: index
            for index, key in enumerate(kulcsok_26)
            if key in egyedi_kulcsok
        }

        # Csak akkor fogadjuk el a párosítást, ha a kihagyott
        # mezők közül legalább egy ténylegesen eltér.
        must_differ = level["must_differ"]

        tenyleges_egyezesi_kulcsok = {
            key
            for key in egyedi_kulcsok
            if any(
                maradek_22.iloc[lookup_22[key]][field]
                != maradek_26.iloc[lookup_26[key]][field]
                for field in must_differ
            )
        }

        # Többszörös kulcsok naplózása.
        for key in ambig_kulcsok:

            tobbszoros_kulcsok.append({
                "egyezesi_szint": level_name,
                "kulcs_mezoi": "; ".join(keys),
                "kulcs_erteke": " | ".join(key),
                "darab_2022": counts_22[key],
                "darab_2026": counts_26[key],
                "eredmeny_csv": f"{level_name}.csv",
            })

        # Kétértelmű rekordok keresése.
        for side, frame, counts in [
            ("2022", maradek_22, counts_22),
            ("2026", maradek_26, counts_26),
        ]:

            mask = [
                tuple(row) in ambig_kulcsok
                for row in frame[keys].itertuples(
                    index=False,
                    name=None,
                )
            ]

            ambiguous_rows = frame.loc[
                mask,
                ["_record_id"] + keys,
            ]

            for row in ambiguous_rows.itertuples(
                index=False,
                name=None,
            ):

                record_id = row[0]
                key = tuple(row[1:])

                ketertelmu_cimek.append({
                    "egyezesi_szint": level_name,
                    "oldal": side,
                    "record_id": record_id,
                    "kulcs_erteke": " | ".join(key),
                    "darab_azonos_kulcs": counts[key],
                    "eredmeny_csv": f"{level_name}.csv",
                })

        # Egyezési sorok létrehozása.
        matches = []

        for key in tenyleges_egyezesi_kulcsok:

            row22 = maradek_22.iloc[lookup_22[key]]
            row26 = maradek_26.iloc[lookup_26[key]]

            matches.append(
                create_match_row(row22, row26, level_name)
            )

        matches_df = pd.DataFrame(
            matches,
            columns=OUTPUT_COLUMNS,
        )

        matches_df.to_csv(
            OUTPUT_DIR / f"{level_name}.csv",
            index=False,
            encoding="utf-8-sig",
        )

        print(f"Talált egyedi egyezések: {len(matches_df):,}")
        print(f"Többszörös kulcsok: {len(ambig_kulcsok):,}")

        # A ténylegesen párosított rekordokat eltávolítjuk
        # a következő szint előtt.
        matched_ids_22 = {
            maradek_22.iloc[lookup_22[key]]["_record_id"]
            for key in tenyleges_egyezesi_kulcsok
        }

        matched_ids_26 = {
            maradek_26.iloc[lookup_26[key]]["_record_id"]
            for key in tenyleges_egyezesi_kulcsok
        }

        maradek_22 = maradek_22[
            ~maradek_22["_record_id"].isin(matched_ids_22)
        ].copy()

        maradek_26 = maradek_26[
            ~maradek_26["_record_id"].isin(matched_ids_26)
        ].copy()

        elapsed = time.time() - start_time
        print(f"Futási idő: {elapsed:.2f} másodperc")

    return (
        maradek_22,
        maradek_26,
        tobbszoros_kulcsok,
        ketertelmu_cimek,
    )


# ==================================================
# 8. FŐ FELDOLGOZÁSI FOLYAMAT
# ==================================================

def build(adat22=None, adat26=None):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nSzintenkénti párosítás indítása...")

    # Beolvasás, ha nem kaptunk DataFrame-et.
    if adat22 is None:

        print("2022-es maradék címek beolvasása...")

        adat22 = pd.read_csv(
            FILE_22,
            dtype=str,
            encoding="utf-8-sig",
        )

    if adat26 is None:

        print("2026-os maradék címek beolvasása...")

        adat26 = pd.read_csv(
            FILE_26,
            dtype=str,
            encoding="utf-8-sig",
        )

    print(f"2022-es címek: {len(adat22):,}")
    print(f"2026-os címek: {len(adat26):,}")

    # Normalizálás.
    print("\nCímek normalizálása...")

    adat22 = prepare_data(adat22)
    adat26 = prepare_data(adat26)

    # Szintenkénti egyeztetés.
    (
        maradek_22,
        maradek_26,
        tobbszoros_kulcsok,
        ketertelmu_cimek,
    ) = match_by_levels(adat22, adat26)

    # ==================================================
    # 9. TÖBBSZÖRÖS KULCSOK ÉS KÉTÉRTELMŰ CÍMEK MENTÉSE
    # ==================================================

    pd.DataFrame(tobbszoros_kulcsok).to_csv(
        OUTPUT_DIR / "tobbszoros_kulcsok.csv",
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(ketertelmu_cimek).to_csv(
        OUTPUT_DIR / "ketertelmu_cimek.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # ==================================================
    # 10. MARADÉK CÍMEK MENTÉSE
    # ==================================================

    helper_columns = [
        col + "_norm" for col in NORMALIZATION
    ] + ["_record_id"]

    maradek_22.drop(
        columns=helper_columns,
        errors="ignore",
    ).to_csv(
        OUTPUT_DIR / "maradek_2022.csv",
        index=False,
        encoding="utf-8-sig",
    )

    maradek_26.drop(
        columns=helper_columns,
        errors="ignore",
    ).to_csv(
        OUTPUT_DIR / "maradek_2026.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # ==================================================
    # 11. ÖSSZESÍTÉS
    # ==================================================

    print("\n====================================")
    print("ÖSSZESÍTÉS")
    print("====================================")

    print(f"Maradék 2022-es címek: {len(maradek_22):,}")
    print(f"Maradék 2026-os címek: {len(maradek_26):,}")
    print(f"Többszörös kulcsok száma: {len(tobbszoros_kulcsok):,}")
    print(f"Kétértelmű rekordok száma: {len(ketertelmu_cimek):,}")

    print(f"\nEredmények mentési helye: {OUTPUT_DIR}")

    return maradek_22, maradek_26


# ==================================================
# 12. ÖNÁLLÓ FUTTATÁS
# ==================================================

if __name__ == "__main__":
    build()
