from download_data import main as download_main
from build_reference_tables import main as build_main
from finding_matches import main as matches_main


def main():
    sikeres = download_main()

    if sikeres is not True:
        print("A letöltés nem fejeződött be sikeresen. A táblák építése kimarad.")
        return

    build_main()
    matches_main()


if __name__ == "__main__":
    main()