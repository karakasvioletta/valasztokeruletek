import pandas as pd
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, FILE_2022, FILE_2026


fajl_2022 = FILE_2022
fajl_2026 = FILE_2026


PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

kimenet22_fajl = PROCESSED_DATA_DIR / "szavazokorok_2022.csv"
kimenet26_fajl = PROCESSED_DATA_DIR / "szavazokorok_2026.csv"

def csv_beolvasasa(fajl, szukseges_oszlopok):
    """CSV beolvasása az elválasztójel automatikus felismerésével."""
    fejlec = pd.read_csv(
        fajl,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        nrows=0,
    )

    # Az oszlopnevek elejéről és végéről eltávolítjuk a szóközöket.
    fejlec_oszlopok = [oszlop.strip() for oszlop in fejlec.columns]

    # Megnézzük, hogy minden szükséges oszlop létezik-e.
    hianyzo = [
        oszlop for oszlop in szukseges_oszlopok
        if oszlop not in fejlec_oszlopok
    ]

    if hianyzo:
        raise ValueError(
            f"A(z) {fajl.name} fájlban nem találhatók ezek az oszlopok: "
            f"{hianyzo}\n"
            f"A fájl oszlopai: {fejlec_oszlopok}"
        )

    return pd.read_csv(
        fajl,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        dtype=str,
        usecols=szukseges_oszlopok,
    )


print("2022-es adatok betöltése...")

adat22 = csv_beolvasasa(
    fajl_2022,
    [
        "MEGYE_KÓD",
        "TELEPÜLÉS_KÓD",
        "OEVK",
        "SZAVAZÓKÖR_SORSZÁM",
        "SZAVAZÓKÖR_CÍM",
    ],
)

print("2026-os adatok betöltése...")

adat26 = csv_beolvasasa(
    fajl_2026,
    [
        "Vármegye kód",
        "Település kód",
        "OEVK",
        "Szavazókör",
        "Szavazókör cím",
    ],
)

# Településazonosító létrehozása.
# A kódokat szövegként kezeljük, hogy a kezdő nullák megmaradjanak.
for adat, megye_oszlop, telepules_oszlop in [
    (adat22, "MEGYE_KÓD", "TELEPÜLÉS_KÓD"),
    (adat26, "Vármegye kód", "Település kód"),
]:
    adat[megye_oszlop] = adat[megye_oszlop].fillna("").str.strip()
    adat[telepules_oszlop] = adat[telepules_oszlop].fillna("").str.strip()

    adat["település_azonosító"] = (
        adat[megye_oszlop] + adat[telepules_oszlop]
    )

# A 2022-es kimeneti tábla elkészítése.
kimenet22 = adat22[
    [
        "település_azonosító",
        "OEVK",
        "SZAVAZÓKÖR_SORSZÁM",
        "SZAVAZÓKÖR_CÍM",
    ]
].copy()

kimenet22 = kimenet22.fillna("").astype(str).apply(
    lambda oszlop: oszlop.str.strip()
).drop_duplicates()

kimenet22 = kimenet22.sort_values(
    ["település_azonosító", "OEVK", "SZAVAZÓKÖR_SORSZÁM"]
)

kimenet22.to_csv(
    kimenet22_fajl,
    index=False,
    encoding="utf-8-sig",
)

# A 2026-os kimeneti tábla elkészítése.
kimenet26 = adat26[
    [
        "település_azonosító",
        "OEVK",
        "Szavazókör",
        "Szavazókör cím",
    ]
].copy()

kimenet26 = kimenet26.fillna("").astype(str).apply(
    lambda oszlop: oszlop.str.strip()
).drop_duplicates()

kimenet26 = kimenet26.sort_values(
    ["település_azonosító", "OEVK", "Szavazókör"]
)

kimenet26.to_csv(
    kimenet26_fajl,
    index=False,
    encoding="utf-8-sig",
)

print("\nElkészült a két kimeneti fájl!")
print(f"2022-es rekordok száma: {len(kimenet22):,}")
print(f"2026-os rekordok száma: {len(kimenet26):,}")
print("Mentési hely:", PROCESSED_DATA_DIR)
