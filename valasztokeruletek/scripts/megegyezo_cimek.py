import sys
from pathlib import Path

import pandas as pd

# A projekt gyökérmappájának hozzáadása a Python keresési útvonalához
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import PROCESSED_DATA_DIR, FILE_2022, FILE_2026


def build(adat22=None, adat26=None):

    if adat22 is None:
        adat22 = pd.read_csv(
            FILE_2022,
            sep=None,
            engine="python",
            dtype=str,
            encoding="utf-8-sig",
        )
        adat22.columns = adat22.columns.str.strip()

    if adat26 is None:
        adat26 = pd.read_csv(
            FILE_2026,
            sep=None,
            engine="python",
            dtype=str,
            encoding="utf-8-sig",
        )
        adat26.columns = adat26.columns.str.strip()

    kimenet = PROCESSED_DATA_DIR / "egyezo_cimek_22_26.csv"

    print(f"2022-es sorok: {len(adat22):,}")
    print(f"2026-os sorok: {len(adat26):,}")

    # ==================================================
    # 1. SZÜKSÉGES OSZLOPOK KIVÁLASZTÁSA
    # ==================================================

    oszlopok22 = [
        "MEGYE_KÓD",
        "TELEPÜLÉS_KÓD",
        "KÖZTERÜLET_NÉV",
        "KÖZTERÜLET_JELLEG",
        "HÁZSZÁM",
        "ÉPÜLET",
        "LÉPCSŐHÁZ",
        "SZAVAZÓKÖR_SORSZÁM",
        "OEVK",
    ]

    oszlopok26 = [
        "Vármegye kód",
        "Település kód",
        "Közterület név",
        "Közterület jelleg",
        "Házszám",
        "Épület",
        "Lépcsőház",
        "Szavazókör",
        "OEVK",
    ]

    # Csak a szükséges oszlopokat tartjuk meg.
    # A copy() miatt az eredeti, közös DataFrame-ek nem módosulnak.
    adat22 = adat22[oszlopok22].copy()
    adat26 = adat26[oszlopok26].copy()

    # ==================================================
    # 2. OSZLOPOK ÁTNEVEZÉSE
    # ==================================================

    adat22 = adat22.rename(columns={
        "MEGYE_KÓD": "megye_kód",
        "TELEPÜLÉS_KÓD": "település_kód",
        "KÖZTERÜLET_NÉV": "közterület_neve",
        "KÖZTERÜLET_JELLEG": "közterület_jellege",
        "HÁZSZÁM": "házszám",
        "ÉPÜLET": "épület",
        "LÉPCSŐHÁZ": "lépcsőház",
        "SZAVAZÓKÖR_SORSZÁM": "szavazókör_22",
        "OEVK": "OEVK_22",
    })

    adat26 = adat26.rename(columns={
        "Vármegye kód": "megye_kód",
        "Település kód": "település_kód",
        "Közterület név": "közterület_neve",
        "Közterület jelleg": "közterület_jellege",
        "Házszám": "házszám",
        "Épület": "épület",
        "Lépcsőház": "lépcsőház",
        "Szavazókör": "szavazókör_26",
        "OEVK": "OEVK_26",
    })

    # ==================================================
    # 3. EGYEZÉSI KULCSOK
    # ==================================================

    kulcsok = [
        "megye_kód",
        "település_kód",
        "közterület_neve",
        "közterület_jellege",
        "házszám",
        "épület",
        "lépcsőház",
    ]

    # Településazonosító létrehozása
    adat22["település_azonosító"] = (
        adat22["megye_kód"] + adat22["település_kód"]
    )

    adat26["település_azonosító"] = (
        adat26["megye_kód"] + adat26["település_kód"]
    )

    # ==================================================
    # 4. DUPLIKÁCIÓK ELLENŐRZÉSE
    # ==================================================

    dupl22 = adat22.duplicated(subset=kulcsok, keep=False)
    dupl26 = adat26.duplicated(subset=kulcsok, keep=False)

    print(f"2022-ben ismétlődő címkulcsú sorok: {dupl22.sum()}")
    print(f"2026-ban ismétlődő címkulcsú sorok: {dupl26.sum()}")

    if dupl22.any() or dupl26.any():
        print(
            "FIGYELEM: egy cím több rekordban is szerepelhet. "
            "A párosítás több sort is eredményezhet."
        )

    # ==================================================
    # 5. EGYEZÉSEK VIZSGÁLATA MEZŐNKÉNT
    # ==================================================

    print("\nEGYEZÉSEK VIZSGÁLATA MEZŐNKÉNT")

    vizsgalt_kulcsok = [
        "megye_kód",
        "település_kód",
        "közterület_neve",
        "közterület_jellege",
        "házszám",
        "épület",
        "lépcsőház",
    ]

    for i in range(1, len(vizsgalt_kulcsok) + 1):

        aktualis_kulcsok = vizsgalt_kulcsok[:i]

        egyezesek = adat22[aktualis_kulcsok].drop_duplicates().merge(
            adat26[aktualis_kulcsok].drop_duplicates(),
            on=aktualis_kulcsok,
            how="inner",
        )

        print(
            f"{', '.join(aktualis_kulcsok)}: "
            f"{len(egyezesek)} egyedi kulcskombináció"
        )

       # ==================================================
    # 6. CÍMEK ÖSSZEFÉSÜLÉSE ÉS ELTÉRÉSEK KIGYŰJTÉSE
    # ==================================================

    print("\nAz egyező címek és az eltérések keresése...")

    # A két adatbázis összefésülése.
    # Az outer típus az összes címet megtartja:
    # - ami mindkét évben szerepel,
    # - ami csak 2022-ben szerepel,
    # - ami csak 2026-ban szerepel.

    osszefesult = adat22.merge(
        adat26,
        on=kulcsok,
        how="outer",
        suffixes=("_22", "_26"),
        indicator=True,
    )

    # A cím mindkét évben szerepel?
    mindket_evben = osszefesult["_merge"] == "both"

    # Csak a szavazókör változott?
    szavazokor_valtozas = (
        mindket_evben
        & (
            osszefesult["szavazókör_22"]
            != osszefesult["szavazókör_26"]
        )
    )

    # Csak az OEVK változott?
    oevk_valtozas = (
        mindket_evben
        & (
            osszefesult["OEVK_22"]
            != osszefesult["OEVK_26"]
        )
    )

    # Csak a 2022-es adatbázisban szereplő címek
    csak_2022 = osszefesult["_merge"] == "left_only"

    # Csak a 2026-os adatbázisban szereplő címek
    csak_2026 = osszefesult["_merge"] == "right_only"

    # Eltérő rekordok kiválasztása
    elteresek = osszefesult[
        szavazokor_valtozas
        | oevk_valtozas
        | csak_2022
        | csak_2026
    ].copy()

    # Eltérés típusának meghatározása
    elteresek["eltérés_típusa"] = ""

    elteresek.loc[
        szavazokor_valtozas,
        "eltérés_típusa",
    ] = "Megváltozott a szavazókör"

    elteresek.loc[
        oevk_valtozas,
        "eltérés_típusa",
    ] = elteresek.loc[
        oevk_valtozas,
        "eltérés_típusa",
    ].apply(
        lambda x: (
            x + "; megváltozott az OEVK"
            if x
            else "Megváltozott az OEVK"
        )
    )

    elteresek.loc[
        csak_2022,
        "eltérés_típusa",
    ] = "Csak a 2022-es adatbázisban szerepel"

    elteresek.loc[
        csak_2026,
        "eltérés_típusa",
    ] = "Csak a 2026-os adatbázisban szerepel"

    # Településazonosító létrehozása az eltérésekhez
    # A merge során a közös kulcsoszlopok nem kaptak évjelölést.

    elteresek["település_azonosító"] = (
        elteresek["megye_kód"].fillna("")
        + elteresek["település_kód"].fillna("")
    )

    # A csak az egyik évben szereplő címeknél
    # jelöljük, melyik adatbázisban találhatók.
    elteresek["adatforrás"] = elteresek["_merge"].map({
        "left_only": "2022",
        "right_only": "2026",
        "both": "Mindkét év",
    })

    # Kimeneti oszlopok
    elteresek = elteresek[
        [
            "település_azonosító",
            "közterület_neve",
            "közterület_jellege",
            "házszám",
            "épület",
            "lépcsőház",
            "szavazókör_22",
            "szavazókör_26",
            "OEVK_22",
            "OEVK_26",
            "adatforrás",
            "eltérés_típusa",
        ]
    ]

    # Rendezés
    elteresek = elteresek.sort_values(
        [
            "település_azonosító",
            "közterület_neve",
            "közterület_jellege",
            "házszám",
        ],
        na_position="last",
    ).reset_index(drop=True)

    # Eltérések mentése külön CSV-be
    elteres_kimenet = (
        PROCESSED_DATA_DIR / "eltero_cimek_22_26.csv"
    )

    elteresek.to_csv(
        elteres_kimenet,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nELTÉRÉSEK ÖSSZESÍTÉSE")
    print(
        "Megváltozott szavazókör:",
        int(szavazokor_valtozas.sum()),
    )
    print(
        "Megváltozott OEVK:",
        int(oevk_valtozas.sum()),
    )
    print(
        "Csak 2022-ben szereplő címek:",
        int(csak_2022.sum()),
    )
    print(
        "Csak 2026-ban szereplő címek:",
        int(csak_2026.sum()),
    )
    print(f"Összes eltérő rekord: {len(elteresek):,}")
    print(f"Eltérések fájlja: {elteres_kimenet}")

    # ==================================================
    # 7. KIMENETI OSZLOPOK
    # ==================================================

    eredmeny = eredmeny[
        [
            "település_azonosító_22",
            "közterület_neve",
            "közterület_jellege",
            "házszám",
            "épület",
            "lépcsőház",
            "szavazókör_22",
            "szavazókör_26",
            "OEVK_22",
            "OEVK_26",
        ]
    ].rename(columns={
        "település_azonosító_22": "település_azonosító",
    })

    eredmeny = eredmeny.sort_values(
        [
            "település_azonosító",
            "közterület_neve",
            "közterület_jellege",
            "házszám",
            "épület",
            "lépcsőház",
        ]
    ).reset_index(drop=True)

    # ==================================================
    # 8. MENTÉS
    # ==================================================

    eredmeny.to_csv(
        kimenet,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nKÉSZ!")
    print(f"Egyező rekordpárok száma: {len(eredmeny):,}")
    print(f"Kimeneti fájl: {kimenet}")
    print("\nAz első 10 rekord:")
    print(eredmeny.head(10).to_string(index=False))

if __name__ == "__main__":
    build()