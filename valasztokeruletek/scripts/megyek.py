
import pandas as pd
from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, FILE_2022


bemenet = FILE_2022
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
kimenet = PROCESSED_DATA_DIR / "megyek.csv"

print("2022-es adatbázis beolvasása...")

df = pd.read_csv(
    bemenet,
    dtype=str,
    encoding="utf-8-sig",
    usecols=["MEGYE", "MEGYE_KÓD"]
)

# Oszlopok tisztítása
for oszlop in ["MEGYE", "MEGYE_KÓD"]:
    df[oszlop] = df[oszlop].fillna("").str.strip()

# Üres rekordok elhagyása
df = df[
    (df["MEGYE"] != "")
    & (df["MEGYE_KÓD"] != "")
]

# Egyedi megye–kód párok
megyek = (
    df[["MEGYE_KÓD", "MEGYE"]]
    .drop_duplicates()
    .sort_values(["MEGYE_KÓD", "MEGYE"])
    .reset_index(drop=True)
)

# Ha egy megye több különböző kóddal szerepel, jelezzük
duplikalt_nevek = megyek[
    megyek.duplicated(subset=["MEGYE"], keep=False)
]
duplikalt_kodok = megyek[
    megyek.duplicated(subset=["MEGYE_KÓD"], keep=False)
]

if not duplikalt_nevek.empty:
    print("FIGYELEM: Egy megye több kóddal szerepel:")
    print(duplikalt_nevek.to_string(index=False))

if not duplikalt_kodok.empty:
    print("FIGYELEM: Egy kód több megyéhez tartozik:")
    print(duplikalt_kodok.to_string(index=False))

# Oszlopnevek a kimeneti fájlban
megyek = megyek.rename(columns={
    "MEGYE_KÓD": "megye_kód",
    "MEGYE": "megye"
})

megyek.to_csv(kimenet, index=False, encoding="utf-8-sig")

print(f"Elkészült: {kimenet}")
print(f"Megyesorok száma: {len(megyek)}")
print(megyek.to_string(index=False))
