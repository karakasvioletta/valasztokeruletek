import pandas as pd
from config import REFERENCE_TABLES_DIR, FILE_2022

def build(adat22):
    if adat22 is None:
        adat22 = pd.read_csv(
            FILE_2022,
            dtype=str,
            encoding="utf-8-sig",
            usecols=[
                "MEGYE_KÓD",
                "TELEPÜLÉS_KÓD",
                "TELEPÜLÉS",
            ],
        )

        for oszlop in [
            "MEGYE_KÓD",
            "TELEPÜLÉS_KÓD",
            "TELEPÜLÉS",
        ]:
            adat22[oszlop] = adat22[oszlop].fillna("").str.strip()
    
    kimenet = REFERENCE_TABLES_DIR / "telepulesek.csv"

    # Szükséges oszlopok kiválasztása
    df = adat22[
        ["MEGYE_KÓD", "TELEPÜLÉS_KÓD", "TELEPÜLÉS"]
    ].copy()

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

    # Egyedi településazonosító létrehozása
    telepulesek["település_azonosító"] = (
        telepulesek["MEGYE_KÓD"]
        + telepulesek["TELEPÜLÉS_KÓD"]
    )

    # Ellenőrzés: egy azonosítóhoz csak egy település tartozzon
    duplikalt = telepulesek[
        telepulesek.duplicated(
            subset=["település_azonosító"],
            keep=False,
        )
    ].sort_values("település_azonosító")

    if not duplikalt.empty:
        print("FIGYELEM: Nem egyedi településazonosítók!")
        print(duplikalt.to_string(index=False))
    else:
        print("Minden településazonosító egyedi.")

    # Oszlopnevek átnevezése
    telepulesek = telepulesek.rename(columns={
        "MEGYE_KÓD": "megye_kód",
        "TELEPÜLÉS_KÓD": "település_kód",
        "TELEPÜLÉS": "település",
    })

    # Végleges oszlopok és sorrend
    telepulesek = telepulesek[
        [
            "település_azonosító",
            "település",
        ]
    ].sort_values(
        ["település_azonosító"]
    ).reset_index(drop=True)

    telepulesek.to_csv(
        kimenet,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Elkészült: {kimenet}")
    print(f"Településsorok száma: {len(telepulesek)}")
    print(telepulesek.head(10).to_string(index=False))

if __name__ == "__main__":
    build()