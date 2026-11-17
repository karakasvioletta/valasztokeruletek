
from download_data import main as download_main
from build_reference_tables import main as build_main
from finding_matches import main as matches_main


def main():

    print("\n" + "=" * 60)
    print("VÁLASZTÓKERÜLETI ADATFELDOLGOZÁS")
    print("=" * 60)

    # 1. Adatok letöltése
    print("\n1. ADATOK LETÖLTÉSE")
    sikeres = download_main()

    if not sikeres:
        print(
            "\nA szükséges adatfájlok nem állnak rendelkezésre. "
            "A további feldolgozás leáll."
        )
        return

    # 2. Referencia-táblák létrehozása
    print("\n2. REFERENCIA-TÁBLÁK LÉTREHOZÁSA")
    build_main()

    # 3. Címek párosítása
    print("\n3. CÍMEK ÖSSZEHASONLÍTÁSA ÉS PÁROSÍTÁSA")
    matches_main()

    print("\n" + "=" * 60)
    print("A TELJES ADATFELDOLGOZÁS ELKÉSZÜLT!")
    print("=" * 60)


if __name__ == "__main__":
    main()
