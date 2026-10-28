
import pandas as pd
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, FILE_2022, FILE_2026

# ==================================================
# 1. FÁJLOK
# ==================================================


fajl22 = FILE_2022
fajl26 = FILE_2026

PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
kimenet = PROCESSED_DATA_DIR / "egyezo_cimek_22_26.csv"


# ==================================================
# 2. BEOLVASÁS
# ==================================================

print("2022-es adatbázis beolvasása...")

adat22 = pd.read_csv(
    fajl22,
    sep=None,
    engine="python",
    dtype=str,
    encoding="utf-8-sig"
)

print("2026-os adatbázis beolvasása...")

adat26 = pd.read_csv(
    fajl26,
    sep=None,
    engine="python",
    dtype=str,
    encoding="utf-8-sig"
)

adat22.columns = adat22.columns.str.strip()
adat26.columns = adat26.columns.str.strip()

print(f"2022-es sorok: {len(adat22)}")
print(f"2026-os sorok: {len(adat26)}")


# ==================================================
# 3. SZÜKSÉGES OSZLOPOK
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
    "OEVK"
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
    "OEVK"
]

hianyzo22 = [o for o in oszlopok22 if o not in adat22.columns]
hianyzo26 = [o for o in oszlopok26 if o not in adat26.columns]

if hianyzo22:
    raise ValueError(
        f"Hiányzó 2022-es oszlopok: {hianyzo22}\n"
        f"Elérhető oszlopok: {adat22.columns.tolist()}"
    )

if hianyzo26:
    raise ValueError(
        f"Hiányzó 2026-os oszlopok: {hianyzo26}\n"
        f"Elérhető oszlopok: {adat26.columns.tolist()}"
    )


# ==================================================
# 4. OSZLOPOK ÁTNEVEZÉSE
# ==================================================

adat22 = adat22[oszlopok22].rename(columns={
    "MEGYE_KÓD": "megye_kód",
    "TELEPÜLÉS_KÓD": "település_kód",
    "KÖZTERÜLET_NÉV": "közterület_neve",
    "KÖZTERÜLET_JELLEG": "közterület_jellege",
    "HÁZSZÁM": "házszám",
    "ÉPÜLET": "épület",
    "LÉPCSŐHÁZ": "lépcsőház",
    "SZAVAZÓKÖR_SORSZÁM": "szavazókör_22",
    "OEVK": "OEVK_22"
})

adat26 = adat26[oszlopok26].rename(columns={
    "Vármegye kód": "megye_kód",
    "Település kód": "település_kód",
    "Közterület név": "közterület_neve",
    "Közterület jelleg": "közterület_jellege",
    "Házszám": "házszám",
    "Épület": "épület",
    "Lépcsőház": "lépcsőház",
    "Szavazókör": "szavazókör_26",
    "OEVK": "OEVK_26"
})


# ==================================================
# 5. MEZŐK EGYSÉGESÍTÉSE
# ==================================================

kulcsok = [
    "megye_kód",
    "település_kód",
    "közterület_neve",
    "közterület_jellege",
    "házszám",
    "épület",
    "lépcsőház"
]

# Az üres értékeket egységesen kezeljük.
# A szóközök elejéről és végéről eltávolítjuk a felesleget.
for df in [adat22, adat26]:
    for oszlop in df.columns:
        df[oszlop] = (
            df[oszlop]
            .fillna("")
            .astype(str)
            .str.strip()
        )

# Településazonosító előállítása mindkét évben
adat22["település_azonosító"] = (
    adat22["megye_kód"] + adat22["település_kód"]
)

adat26["település_azonosító"] = (
    adat26["megye_kód"] + adat26["település_kód"]
)


# ==================================================
# 6. DUPLIKÁCIÓK ELLENŐRZÉSE
# ==================================================

dupl22 = adat22.duplicated(subset=kulcsok, keep=False)
dupl26 = adat26.duplicated(subset=kulcsok, keep=False)

print(f"2022-ben ismétlődő címkulcsú sorok: {dupl22.sum()}")
print(f"2026-ban ismétlődő címkulcsú sorok: {dupl26.sum()}")

if dupl22.any() or dupl26.any():
    print(
        "FIGYELEM: egy cím több rekordban is szerepelhet. "
        "A kód ezeket nem törli; a párosítás több sort is eredményezhet."
    )


# ==================================================
# 7. AZONOS CÍMEK ÖSSZEFÉSÜLÉSE
# ==================================================

print("Az egyező címek keresése...")

# Csak azokat a rekordokat tartjuk meg, amelyeknél
# mind a hét cím- és kódmező egyezik.
eredmeny = adat22.merge(
    adat26,
    on=kulcsok,
    how="inner",
    suffixes=("_22", "_26")
)

# Ha a megye- és településkódok egyeznek,
# az azonosító mindkét évben azonos kell legyen.
azonosito_egyezes = (
    eredmeny["település_azonosító_22"]
    == eredmeny["település_azonosító_26"]
)

if not azonosito_egyezes.all():
    print("FIGYELEM: eltérés van a generált településazonosítók között!")


# ==================================================
# 8. KIMENETI OSZLOPOK
# ==================================================

eredmeny = eredmeny[[
    "település_azonosító_22",
    "közterület_neve",
    "közterület_jellege",
    "házszám",
    "épület",
    "lépcsőház",
    "szavazókör_22",
    "szavazókör_26",
    "OEVK_22",
    "OEVK_26"
]].rename(columns={
    "település_azonosító_22": "település_azonosító"
})

# Rendezés településazonosító és cím szerint
eredmeny = eredmeny.sort_values(
    [
        "település_azonosító",
        "közterület_neve",
        "közterület_jellege",
        "házszám",
        "épület",
        "lépcsőház"
    ]
).reset_index(drop=True)


# ==================================================
# 9. MENTÉS ÉS ÖSSZESÍTÉS
# ==================================================

eredmeny.to_csv(
    kimenet,
    index=False,
    encoding="utf-8-sig"
)

print("\nKÉSZ!")
print(f"Egyező rekordpárok száma: {len(eredmeny)}")
print(f"Kimeneti fájl: {kimenet}")
print("\nAz első 10 rekord:")
print(eredmeny.head(10).to_string(index=False))
