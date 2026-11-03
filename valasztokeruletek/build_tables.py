import sys
from pathlib import Path
from config import PROCESSED_DATA_DIR, FILE_2022, FILE_2026
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from scripts.megyek import build as build_megyek
from scripts.telepulesek import build as build_telepulesek
from scripts.megegyezo_cimek import build as build_megegyezo_cimek
from scripts.szavazokorok import build as build_szavazokorok


# A négy script által együttesen használt oszlopok
OSZLOPOK_2022 = [
    "MEGYE",
    "MEGYE_KÓD",
    "TELEPÜLÉS_KÓD",
    "TELEPÜLÉS",
    "KÖZTERÜLET_NÉV",
    "KÖZTERÜLET_JELLEG",
    "HÁZSZÁM",
    "ÉPÜLET",
    "LÉPCSŐHÁZ",
    "SZAVAZÓKÖR_SORSZÁM",
    "SZAVAZÓKÖR_CÍM",
    "OEVK",
]

OSZLOPOK_2026 = [
    "Vármegye kód",
    "Település kód",
    "Közterület név",
    "Közterület jelleg",
    "Házszám",
    "Épület",
    "Lépcsőház",
    "Szavazókör",
    "Szavazókör cím",
    "OEVK",
]


def csv_beolvasasa(fajl, szukseges_oszlopok):
    """
    CSV egyszeri beolvasása.
    Automatikusan felismeri az elválasztójelet,
    és csak a szükséges oszlopokat tölti be.
    """

    print(f"Oszlopok ellenőrzése: {fajl.name}")

    # Fejléc beolvasása az elválasztójel felismeréséhez
    fejlec = pd.read_csv(
        fajl,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        nrows=0,
    )

    elerheto_oszlopok = [
        oszlop.strip() for oszlop in fejlec.columns
    ]

    hianyzo = [
        oszlop
        for oszlop in szukseges_oszlopok
        if oszlop not in elerheto_oszlopok
    ]

    if hianyzo:
        raise ValueError(
            f"A(z) {fajl.name} fájlból hiányoznak a szükséges oszlopok: "
            f"{hianyzo}\n"
            f"Elérhető oszlopok: {elerheto_oszlopok}"
        )

    print(f"Adatok beolvasása: {fajl.name}")

    # A tényleges adatokat már csak egyszer olvassuk be.
    df = pd.read_csv(
        fajl,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        dtype=str,
        usecols=lambda oszlop: oszlop.strip() in szukseges_oszlopok,
    )

    # Oszlopnevek és értékek tisztítása
    df.columns = df.columns.str.strip()

    for oszlop in df.columns:
        df[oszlop] = (
            df[oszlop]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    return df


def main():

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("2022-es adatbázis beolvasása...")
    adat22 = csv_beolvasasa(FILE_2022, OSZLOPOK_2022)

    print("2026-os adatbázis beolvasása...")
    adat26 = csv_beolvasasa(FILE_2026, OSZLOPOK_2026)

    build_megyek(adat22)
    build_telepulesek(adat22)
    build_megegyezo_cimek(adat22, adat26)
    build_szavazokorok(adat22, adat26)

    print("\nAz összes tábla sikeresen elkészült!")


if __name__ == "__main__":
    main()