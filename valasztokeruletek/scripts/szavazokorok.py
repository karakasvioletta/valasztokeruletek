import pandas as pd
from config import PROCESSED_DATA_DIR, FILE_2022, FILE_2026


def build(adat22=None, adat26=None):

    if adat22 is None:
        adat22 = pd.read_csv(
            FILE_2022,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
            dtype=str,
            usecols=[
                "MEGYE_KÓD",
                "TELEPÜLÉS_KÓD",
                "OEVK",
                "SZAVAZÓKÖR_SORSZÁM",
                "SZAVAZÓKÖR_CÍM",
            ],
        )

    if adat26 is None:
        adat26 = pd.read_csv(
            FILE_2026,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
            dtype=str,
            usecols=[
                "Vármegye kód",
                "Település kód",
                "OEVK",
                "Szavazókör",
                "Szavazókör cím",
            ],
        )

    kimenet22_fajl = PROCESSED_DATA_DIR / "szavazokorok_2022.csv"
    kimenet26_fajl = PROCESSED_DATA_DIR / "szavazokorok_2026.csv"

    # ==================================================
    # 2022-ES SZAVAZÓKÖRÖK
    # ==================================================

    kimenet22 = adat22[
        [
            "MEGYE_KÓD",
            "TELEPÜLÉS_KÓD",
            "OEVK",
            "SZAVAZÓKÖR_SORSZÁM",
            "SZAVAZÓKÖR_CÍM",
        ]
    ].copy()

    # Településazonosító létrehozása
    kimenet22["település_azonosító"] = (
        kimenet22["MEGYE_KÓD"]
        + kimenet22["TELEPÜLÉS_KÓD"]
    )

    # Végleges oszlopok
    kimenet22 = kimenet22[
        [
            "település_azonosító",
            "OEVK",
            "SZAVAZÓKÖR_SORSZÁM",
            "SZAVAZÓKÖR_CÍM",
        ]
    ]

    kimenet22 = (
        kimenet22
        .drop_duplicates()
        .sort_values(
            [
                "település_azonosító",
                "OEVK",
                "SZAVAZÓKÖR_SORSZÁM",
            ]
        )
        .reset_index(drop=True)
    )

    kimenet22.to_csv(
        kimenet22_fajl,
        index=False,
        encoding="utf-8-sig",
    )

    # ==================================================
    # 2026-OS SZAVAZÓKÖRÖK
    # ==================================================

    kimenet26 = adat26[
        [
            "Vármegye kód",
            "Település kód",
            "OEVK",
            "Szavazókör",
            "Szavazókör cím",
        ]
    ].copy()

    # Településazonosító létrehozása
    kimenet26["település_azonosító"] = (
        kimenet26["Vármegye kód"]
        + kimenet26["Település kód"]
    )

    # Végleges oszlopok
    kimenet26 = kimenet26[
        [
            "település_azonosító",
            "OEVK",
            "Szavazókör",
            "Szavazókör cím",
        ]
    ]

    kimenet26 = (
        kimenet26
        .drop_duplicates()
        .sort_values(
            [
                "település_azonosító",
                "OEVK",
                "Szavazókör",
            ]
        )
        .reset_index(drop=True)
    )

    kimenet26.to_csv(
        kimenet26_fajl,
        index=False,
        encoding="utf-8-sig",
    )

    # ==================================================
    # ÖSSZESÍTÉS
    # ==================================================

    print("\nElkészült a két szavazóköri fájl!")
    print(f"2022-es rekordok száma: {len(kimenet22):,}")
    print(f"2026-os rekordok száma: {len(kimenet26):,}")
    print("Mentési hely:", PROCESSED_DATA_DIR)

if __name__ == "__main__":
    build()