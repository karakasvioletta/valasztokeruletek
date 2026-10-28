
import subprocess
import sys
from pathlib import Path

# A projekt gyökérkönyvtára
PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# A config.py és a projekt többi moduljának elérhetővé tétele
sys.path.insert(0, str(PROJECT_ROOT))

# A futtatandó scriptek, a megadott sorrendben
SCRIPTS = [
    "megyek.py",
    "telepulesek.py",
    "megegyezo_cimek.py",
    "szavazokorok.py",
]


def main():
    for script_name in SCRIPTS:
        script_path = SCRIPTS_DIR / script_name

        if not script_path.exists():
            print(f"HIBA: Nem található a fájl: {script_path}")
            sys.exit(1)

        print(f"\n{'=' * 60}")
        print(f"Futtatás: {script_name}")
        print(f"{'=' * 60}")

        # A projekt gyökérkönyvtárát hozzáadjuk a PYTHONPATH-hoz
        env = None
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            str(PROJECT_ROOT)
            + os.pathsep
            + env.get("PYTHONPATH", "")
        )

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            env=env,
        )

        if result.returncode != 0:
            print(
                f"\nHIBA: A(z) {script_name} futtatása sikertelen "
                f"(kilépési kód: {result.returncode})."
            )
            sys.exit(result.returncode)

        print(f"Sikeresen lefutott: {script_name}")

    print("\nAz összes táblakészítő script sikeresen lefutott!")


if __name__ == "__main__":
    main()
