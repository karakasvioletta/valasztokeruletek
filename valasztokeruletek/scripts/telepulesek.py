
import pandas as pd
from pathlib import Path
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, FILE_2022



bemenet = FILE_2022

PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
kimenet = PROCESSED_DATA_DIR / "telepulesek.csv"

print("2022-es adatbázis beolvasása...")

df = pd.read_csv(
    bemenet,
    dtype=str,
    encoding="utf-8-sig",
    usecols=["MEGYE_KÓD", "TELEPÜLÉS_KÓD", "TELEPÜLÉS"]
)

# Oszlopok tisztítása
for oszlop in ["MEGYE_KÓD", "TELEPÜLÉS_KÓD", "TELEPÜLÉS"]:
    df[oszlop] = df[oszlop].fillna("").str.strip()

# Hiányos rekordok elhagyása
df = df[
    (df["MEGYE_KÓD"] != "")
    & (df["TELEPÜLÉS_KÓD"] != "")
    & (df["TELEPÜLÉS"] != "")
].copy()

# Egyedi megye–település kód–név kombinációk
telepulesek = df[
    ["MEGYE_KÓD", "TELEPÜLÉS_KÓD", "TELEPÜLÉS"]
].drop_duplicates().copy()

# Egyedi azonosító létrehozása.
# Szövegként kezeljük a kódokat, hogy a kezdő nullák megmaradjanak.
telepulesek["település_azonosító"] = (
    telepulesek["MEGYE_KÓD"]
    + telepulesek["TELEPÜLÉS_KÓD"]
)

# Ellenőrzés: egy azonosítóhoz csak egy település tartozzon
duplikalt = telepulesek[
    telepulesek.duplicated(
        subset=["település_azonosító"],
        keep=False
    )
].sort_values("település_azonosító")

if not duplikalt.empty:
    print("FIGYELEM: Nem egyedi településazonosítók!")
    print(duplikalt.to_string(index=False))
else:
    print("Minden településazonosító egyedi.")

# Végleges oszlopok és sorrend
telepulesek = telepulesek.rename(columns={
    "MEGYE_KÓD": "megye_kód",
    "TELEPÜLÉS_KÓD": "település_kód",
    "TELEPÜLÉS": "település"
})

telepulesek = telepulesek[
    [
        "település_azonosító",
        "település"
    ]
].sort_values(
    ["település_azonosító"]
).reset_index(drop=True)

telepulesek.to_csv(kimenet, index=False, encoding="utf-8-sig")

print(f"Elkészült: {kimenet}")
print(f"Településsorok száma: {len(telepulesek)}")
print(telepulesek.head(10).to_string(index=False))
