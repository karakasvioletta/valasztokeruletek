
import sys
from pathlib import Path
import pandas as pd

# Projekt gyökérmappája
PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from config import PROCESSED_DATA_DIR, MATCHES_DIR


# Mappák
DIFFERENCES_DIR = PROCESSED_DATA_DIR / "differences"

# Bemeneti fájlok – az előző lépés kimenetei
FILE_TELEPULESEK = DIFFERENCES_DIR / "01_telepulesenkent.csv"
FILE_PIR = DIFFERENCES_DIR / "02_pir_szerint.csv"
FILE_KOZTERULET = DIFFERENCES_DIR / "03_kozterulet_neve_szerint.csv"

# Teljes címeket tartalmazó bemeneti fájlok
FILE_2022 = MATCHES_DIR / "csak_2022_cimek.csv"
FILE_2026 = MATCHES_DIR / "csak_2026_cimek.csv"

# Kimeneti fájlok
OUTPUT_FILE = DIFFERENCES_DIR / "egyezesek.csv"
OUTPUT_2022 = DIFFERENCES_DIR / "egyezesek_cimek_2022.csv"
OUTPUT_2026 = DIFFERENCES_DIR / "egyezesek_cimek_2026.csv"


def build(
    telepulesek=None,
    pir=None,
    kozterulet=None,
    df_22=None,
    df_26=None,
):

    # 1. Bemeneti fájlok beolvasása, ha nem kaptunk DataFrame-et

    if telepulesek is None:
        print("Települések beolvasása...")
        telepulesek = pd.read_csv(FILE_TELEPULESEK, dtype=str)

    if pir is None:
        print("PIR-ek beolvasása...")
        pir = pd.read_csv(FILE_PIR, dtype=str)

    if kozterulet is None:
        print("Közterületek beolvasása...")
        kozterulet = pd.read_csv(FILE_KOZTERULET, dtype=str)

    # A különbség oszlopok számmá alakítása
    for df in [telepulesek, pir, kozterulet]:
        df["kulonbseg"] = pd.to_numeric(
            df["kulonbseg"],
            errors="coerce"
        )

    # 2. SZINT: nulla különbségű települések

    nullas_telepulesek = telepulesek[
        telepulesek["kulonbseg"] == 0
    ].copy()

    print(
        f"Nulla különbségű települések: "
        f"{len(nullas_telepulesek):,}"
    )

    # 3. SZINT: ezeken a településeken nulla különbségű PIR-ek

    nullas_pir = pir.merge(
        nullas_telepulesek[["település_azonosító"]],
        on="település_azonosító",
        how="inner"
    )

    nullas_pir = nullas_pir[
        nullas_pir["kulonbseg"] == 0
    ].copy()

    print(
        f"Nulla különbségű PIR-ek: "
        f"{len(nullas_pir):,}"
    )

    # 4. SZINT: ezeken a településeken és PIR-eken
    # nulla különbségű közterületek

    nullas_pir_kulcsok = nullas_pir[
        ["település_azonosító", "PIR"]
    ].drop_duplicates()

    nullas_kozteruletek = kozterulet.merge(
        nullas_pir_kulcsok,
        on=["település_azonosító", "PIR"],
        how="inner"
    )

    nullas_kozteruletek = nullas_kozteruletek[
        nullas_kozteruletek["kulonbseg"] == 0
    ].copy()

    print(
        f"Nulla különbségű közterületek: "
        f"{len(nullas_kozteruletek):,}"
    )

    # Eredmény rendezése
    nullas_kozteruletek = nullas_kozteruletek.sort_values(
        ["település_azonosító", "PIR", "közterület_neve"]
    )

    # 5. SZINT: teljes címeket tartalmazó fájlok beolvasása,
    # ha nem kaptunk DataFrame-et

    if df_22 is None:
        print("\n2022-es teljes címek beolvasása...")
        df_22 = pd.read_csv(FILE_2022, dtype=str)

    if df_26 is None:
        print("2026-os teljes címek beolvasása...")
        df_26 = pd.read_csv(FILE_2026, dtype=str)

    # A nulla különbségű közterületek egyezési kulcsai
    egyezes_kulcsok = nullas_kozteruletek[
        [
            "település_azonosító",
            "PIR",
            "közterület_neve"
        ]
    ].drop_duplicates()

    # 2022-es teljes címek kiválasztása
    cimek_22 = df_22.merge(
        egyezes_kulcsok,
        on=[
            "település_azonosító",
            "PIR",
            "közterület_neve"
        ],
        how="inner"
    )

    # 2026-os teljes címek kiválasztása
    cimek_26 = df_26.merge(
        egyezes_kulcsok,
        on=[
            "település_azonosító",
            "PIR",
            "közterület_neve"
        ],
        how="inner"
    )

    # Teljes címek rendezése
    rendezesi_kulcsok = [
        "település_azonosító",
        "PIR",
        "közterület_neve",
        "házszám"
    ]

    cimek_22 = cimek_22.sort_values(rendezesi_kulcsok)
    cimek_26 = cimek_26.sort_values(rendezesi_kulcsok)

    # 6. Mentés
    DIFFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    cimek_22.to_csv(
        OUTPUT_2022,
        index=False,
        encoding="utf-8-sig"
    )

    cimek_26.to_csv(
        OUTPUT_2026,
        index=False,
        encoding="utf-8-sig"
    )

    nullas_kozteruletek.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # Eredmények kiírása
    print("\nAz összehasonlítás elkészült.")

    print(f"\nNulla különbségű települések: {len(nullas_telepulesek):,}")
    print(f"Nulla különbségű PIR-ek: {len(nullas_pir):,}")
    print(f"Nulla különbségű közterületek: {len(nullas_kozteruletek):,}")

    print(f"\n2022-es kiválasztott teljes címek: {len(cimek_22):,}")
    print(f"2026-os kiválasztott teljes címek: {len(cimek_26):,}")

    print(f"\nEgyezések: {OUTPUT_FILE}")
    print(f"2022-es címek: {OUTPUT_2022}")
    print(f"2026-os címek: {OUTPUT_2026}")

    return nullas_telepulesek, nullas_pir, nullas_kozteruletek, cimek_22, cimek_26


if __name__ == "__main__":
    build()
