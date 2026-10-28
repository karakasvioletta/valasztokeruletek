from download_data import main as download_main
from build_tables import main as build_main


def main():
    sikeres = download_main()

    if sikeres is not True:
        print("A letöltés nem fejeződött be sikeresen. A táblák építése kimarad.")
        return

    build_main()


if __name__ == "__main__":
    main()