import pandas as pd
from config import REFERENCE_TABLES_DIR, FILE_2022



def build(adat22):
    if adat22 is None:
        adat22 = pd.read_csv(
            FILE_2022,
            dtype=str,
            encoding="utf-8-sig",
            usecols=["MEGYE", "MEGYE_KÓD"],
        )

        for oszlop in ["MEGYE", "MEGYE_KÓD"]:
            adat22[oszlop] = adat22[oszlop].fillna("").str.strip()


    kimenet = REFERENCE_TABLES_DIR / "megyek.csv"
    REFERENCE_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # Szükséges oszlopok kiválasztása
    df = adat22[["MEGYE", "MEGYE_KÓD"]].copy()

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

    # Oszlopnevek átnevezése
    megyek = megyek.rename(columns={
        "MEGYE_KÓD": "megye_kód",
        "MEGYE": "megye",
    })

    megyek.to_csv(
        kimenet,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Elkészült: {kimenet}")
    print(f"Megyesorok száma: {len(megyek)}")
    print(megyek.to_string(index=False))

if __name__ == "__main__":
    build()