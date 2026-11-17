
import sys
import re
import unicodedata
from pathlib import Path

import pandas as pd


# ============================================================
# 1. Útvonalak
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from config import PROCESSED_DATA_DIR


DIFFERENCES_DIR = PROCESSED_DATA_DIR / "differences"

FILE_2022 = DIFFERENCES_DIR / "egyezesek_cimek_2022.csv"
FILE_2026 = DIFFERENCES_DIR / "egyezesek_cimek_2026.csv"

OUTPUT_DIR = DIFFERENCES_DIR / "egyezesek_normalizalt"


# ============================================================
# 2. Normalizáló függvények
# ============================================================

def szoveg_normalizalasa(ertek):
    """
    Kisbetűsítés, ékezetek eltávolítása,
    írásjelek egységesítése és szóközök rendezése.
    """

    ertek = str(ertek).strip().lower()

    ertek = unicodedata.normalize("NFKD", ertek)

    ertek = "".join(
        karakter
        for karakter in ertek
        if not unicodedata.combining(karakter)
    )

    ertek = re.sub(r"[^a-z0-9]+", " ", ertek)
    ertek = re.sub(r"\s+", " ", ertek)

    return ertek.strip()


def hazszam_normalizalasa(ertek):
    """
    A házszámból csak az első számsorozatot tartja meg.
    """

    ertek = str(ertek).strip()

    szam = re.match(r"^0*(\d+)", ertek)

    if szam:
        return str(int(szam.group(1)))

    return ""


def egyezesi_kulcs_letrehozasa(df):

    df = df.copy()

    df["_telepules_norm"] = (
        df["település_azonosító"].apply(szoveg_normalizalasa)
    )

    df["_PIR_norm"] = (
        df["PIR"].apply(szoveg_normalizalasa)
    )

    df["_kozterulet_norm"] = (
        df["közterület_neve"].apply(szoveg_normalizalasa)
    )

    df["_hazszam_norm"] = (
        df["házszám"].apply(hazszam_normalizalasa)
    )

    return df


# ============================================================
# 3. Fő feldolgozó függvény
# ============================================================

def build(df_22=None, df_26=None):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Adatok beolvasása, ha nem kaptunk DataFrame-et

    if df_22 is None:
        print("2022-es fájl beolvasása...")
        df_22 = pd.read_csv(
            FILE_2022,
            dtype=str,
            keep_default_na=False
        )

    if df_26 is None:
        print("2026-os fájl beolvasása...")
        df_26 = pd.read_csv(
            FILE_2026,
            dtype=str,
            keep_default_na=False
        )

    # Másolat készítése, hogy az eredeti DataFrame-ek ne módosuljanak
    df_22 = df_22.copy()
    df_26 = df_26.copy()

    df_22["_eredeti_index"] = df_22.index
    df_26["_eredeti_index"] = df_26.index

    print(f"2022-es rekordok: {len(df_22):,}")
    print(f"2026-os rekordok: {len(df_26):,}")

    # Szükséges oszlopok ellenőrzése

    szukseges_oszlopok = [
        "település_azonosító",
        "PIR",
        "közterület_neve",
        "közterület_jellege",
        "házszám",
        "épület",
        "lépcsőház",
    ]

    for ev, df in [("2022", df_22), ("2026", df_26)]:

        hianyzo = [
            oszlop
            for oszlop in szukseges_oszlopok
            if oszlop not in df.columns
        ]

        if hianyzo:
            raise ValueError(
                f"A {ev}-es adatokból hiányoznak ezek az oszlopok: "
                f"{hianyzo}"
            )

    # Normalizált egyezési kulcsok létrehozása

    df_22 = egyezesi_kulcs_letrehozasa(df_22)
    df_26 = egyezesi_kulcs_letrehozasa(df_26)

    KULCSOK = [
        "_telepules_norm",
        "_PIR_norm",
        "_kozterulet_norm",
        "_hazszam_norm",
    ]

    # Hiányos kulcsú rekordok elkülönítése

    def ervenyes_kulcs(df):

        ervenyes = pd.Series(True, index=df.index)

        for oszlop in KULCSOK:
            ervenyes &= df[oszlop] != ""

        return ervenyes

    ervenyes_22 = ervenyes_kulcs(df_22)
    ervenyes_26 = ervenyes_kulcs(df_26)

    print("\nHiányos egyezési kulcsok:")
    print(f"2022: {(~ervenyes_22).sum():,}")
    print(f"2026: {(~ervenyes_26).sum():,}")

    ervenyes_df_22 = df_22.loc[ervenyes_22].copy()
    ervenyes_df_26 = df_26.loc[ervenyes_26].copy()

    # Kulcsok előfordulásának megszámolása

    darab_22 = (
        ervenyes_df_22.groupby(KULCSOK)
        .size()
        .reset_index(name="darab_22")
    )

    darab_26 = (
        ervenyes_df_26.groupby(KULCSOK)
        .size()
        .reset_index(name="darab_26")
    )

    # Csak a mindkét oldalon pontosan egyszer előforduló kulcsok

    egyedi_kulcsok = darab_22.merge(
        darab_26,
        on=KULCSOK,
        how="inner"
    )

    egyedi_kulcsok = egyedi_kulcsok[
        (egyedi_kulcsok["darab_22"] == 1)
        & (egyedi_kulcsok["darab_26"] == 1)
    ][KULCSOK]

    print(f"\nEgyedi közös kulcsok: {len(egyedi_kulcsok):,}")

    # Párosított rekordok kiválasztása

    parositott_22 = ervenyes_df_22.merge(
        egyedi_kulcsok,
        on=KULCSOK,
        how="inner"
    )

    parositott_26 = ervenyes_df_26.merge(
        egyedi_kulcsok,
        on=KULCSOK,
        how="inner"
    )

    # Párosított címek összefűzése

    eredmeny = parositott_22[
        KULCSOK + [
            "település_azonosító",
            "PIR",
            "közterület_neve",
            "közterület_jellege",
            "házszám",
            "épület",
            "lépcsőház",
        ]
    ].merge(
        parositott_26[
            KULCSOK + [
                "közterület_jellege",
                "házszám",
                "épület",
                "lépcsőház",
            ]
        ],
        on=KULCSOK,
        how="inner",
        suffixes=("_22", "_26")
    )

    # Kívánt oszlopnevek és sorrend

    eredmeny = eredmeny.rename(columns={
        "_hazszam_norm": "házszám_normalizált",
    })

    eredmeny = eredmeny[[
        "település_azonosító",
        "PIR",
        "közterület_neve",
        "közterület_jellege_22",
        "közterület_jellege_26",
        "házszám_normalizált",
        "házszám_22",
        "házszám_26",
        "épület_22",
        "épület_26",
        "lépcsőház_22",
        "lépcsőház_26",
    ]]

    # Egyező címek mentése

    eredmeny.to_csv(
        OUTPUT_DIR / "egyezo_cimek.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # Maradék rekordok meghatározása

    parositott_id_22 = set(parositott_22["_eredeti_index"])
    parositott_id_26 = set(parositott_26["_eredeti_index"])

    maradek_22 = df_22.loc[
        ~df_22.index.isin(parositott_id_22)
    ].copy()

    maradek_26 = df_26.loc[
        ~df_26.index.isin(parositott_id_26)
    ].copy()

    # Segédoszlopok eltávolítása

    segedoszlopok = [
        "_telepules_norm",
        "_PIR_norm",
        "_kozterulet_norm",
        "_hazszam_norm",
        "_eredeti_index",
    ]

    maradek_22 = maradek_22.drop(columns=segedoszlopok)
    maradek_26 = maradek_26.drop(columns=segedoszlopok)

    # Maradék rekordok mentése

    maradek_22.to_csv(
        OUTPUT_DIR / "maradek_2022.csv",
        index=False,
        encoding="utf-8-sig"
    )

    maradek_26.to_csv(
        OUTPUT_DIR / "maradek_2026.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # Összesítés

    print("\n" + "=" * 60)
    print("ÖSSZESÍTETT EREDMÉNY")
    print("=" * 60)

    print(f"2022-es eredeti rekordok: {len(df_22):,}")
    print(f"2026-os eredeti rekordok: {len(df_26):,}")

    print(f"\nPárosított címek: {len(eredmeny):,}")

    print(f"Maradék 2022: {len(maradek_22):,}")
    print(f"Maradék 2026: {len(maradek_26):,}")

    print("\nKimeneti mappa:")
    print(OUTPUT_DIR)

    return eredmeny, maradek_22, maradek_26


if __name__ == "__main__":
    build()
