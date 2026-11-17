
import sys
from pathlib import Path

# Projekt gyökérmappájának elérési útja
PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from config import DIFFERENCES_DIR, MATCHES_DIR


# Bemeneti fájlok a matches mappából
FILE_2022_MATCHES = MATCHES_DIR / "csak_2022_cimek.csv"
FILE_2026_MATCHES = MATCHES_DIR / "csak_2026_cimek.csv"


def osszehasonlitas(df_22, df_26, kulcsok, output_fajl):

    # Csoportosítás és címek megszámolása a 2022-es adatokban
    darab_22 = (
        df_22.groupby(kulcsok, dropna=False)
        .size()
        .reset_index(name="csak_2022_db")
    )

    # Csoportosítás és címek megszámolása a 2026-os adatokban
    darab_26 = (
        df_26.groupby(kulcsok, dropna=False)
        .size()
        .reset_index(name="csak_2026_db")
    )

    # A két eredmény összekapcsolása
    eredmeny = darab_22.merge(
        darab_26,
        on=kulcsok,
        how="outer"
    )

    # Hiányzó értékek helyettesítése nullával
    eredmeny["csak_2022_db"] = (
        eredmeny["csak_2022_db"].fillna(0).astype(int)
    )

    eredmeny["csak_2026_db"] = (
        eredmeny["csak_2026_db"].fillna(0).astype(int)
    )

    # Különbség kiszámítása: 2026 - 2022
    eredmeny["kulonbseg"] = (
        eredmeny["csak_2026_db"] - eredmeny["csak_2022_db"]
    )

    # Rendezés
    eredmeny = eredmeny.sort_values(kulcsok)

    # Mentés
    DIFFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DIFFERENCES_DIR / output_fajl
    eredmeny.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"{output_fajl} elkészült: {len(eredmeny):,} sor")

    return eredmeny


def build(df_22=None, df_26=None):

    # Ha nem kapunk DataFrame-et, a matches mappából olvasunk
    if df_22 is None:
        print("2022-es fájl beolvasása...")
        df_22 = pd.read_csv(FILE_2022_MATCHES, dtype=str)

    if df_26 is None:
        print("2026-os fájl beolvasása...")
        df_26 = pd.read_csv(FILE_2026_MATCHES, dtype=str)

    # Szükséges oszlopok ellenőrzése
    szukseges_oszlopok = [
        "település_azonosító",
        "PIR"
    ]

    for ev, df in [("2022", df_22), ("2026", df_26)]:
        hianyzo = [
            oszlop for oszlop in szukseges_oszlopok
            if oszlop not in df.columns
        ]

        if hianyzo:
            raise ValueError(
                f"A {ev}-es fájlból hiányoznak a következő oszlopok: "
                f"{hianyzo}"
            )

    # Közterületnév oszlopok egységesítése
    if "közterület_neve_22" in df_22.columns:
        df_22 = df_22.rename(
            columns={"közterület_neve_22": "közterület_neve"}
        )

    if "közterület_neve_26" in df_26.columns:
        df_26 = df_26.rename(
            columns={"közterület_neve_26": "közterület_neve"}
        )

    print("\nÖsszehasonlítások indítása...")

    # 1. szint: településenként
    eredmeny_1 = osszehasonlitas(
        df_22,
        df_26,
        kulcsok=["település_azonosító"],
        output_fajl="01_telepulesenkent.csv"
    )

    # 2. szint: településenként és PIR szerint
    eredmeny_2 = osszehasonlitas(
        df_22,
        df_26,
        kulcsok=["település_azonosító", "PIR"],
        output_fajl="02_pir_szerint.csv"
    )

    # 3. szint: településenként, PIR és közterület neve szerint
    eredmeny_3 = osszehasonlitas(
        df_22,
        df_26,
        kulcsok=[
            "település_azonosító",
            "PIR",
            "közterület_neve"
        ],
        output_fajl="03_kozterulet_neve_szerint.csv"
    )

    print("\nAz összehasonlítás elkészült.")

    return eredmeny_1, eredmeny_2, eredmeny_3


if __name__ == "__main__":
    build()
