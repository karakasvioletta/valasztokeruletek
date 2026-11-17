
import sys
from pathlib import Path


# ============================================================
# 1. Útvonalak
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"

sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))


# ============================================================
# 2. Feldolgozó függvények importálása
# ============================================================

# Alapvető párosítás
from scripts.alap_parositas.megegyezo_cimek import (
    build as build_megegyezo_cimek
)

# Különbségek összehasonlítása szintenként
from scripts.kulonbsegek_szintenkent.kulonbsegek import (
    build as build_kulonbsegek
)

# Egyező települések, PIR-ek és közterületek kiválasztása
from scripts.kulonbsegek_szintenkent.kulonbsegek_egyezesek import (
    build as build_kulonbsegek_egyezesek
)

# Címek párosítása
from scripts.kulonbsegek_szintenkent.parositas import (
    build as build_parositas
)

# Telejs párosításból kimaradt címek normalizált párosítása
from scripts.normalizalt_egyezesek.normalizalt_egyezesek import (
    build as build_normalizalt_parositas
)

from scripts.szintenkenti_egyezesek.szintenkenti_egyezes import (
    build as build_szintenkenti_parositas
)

# ============================================================
# 3. Teljes folyamat
# ============================================================

def main():

    print("\n" + "=" * 60)
    print("CÍMPÁROSÍTÁSI FOLYAMAT INDÍTÁSA")
    print("=" * 60)

    # 1. Alapvető címek párosítása
    print("\n1. Alapvető címek párosítása...")
    build_megegyezo_cimek()

    # 2. Különbségek összehasonlítása szintenként
    print("\n2. Különbségek összehasonlítása...")
    build_kulonbsegek()

    # 3. Egyező települések, PIR-ek és közterületek kiválasztása
    print("\n3. Egyező címcsoportok kiválasztása...")
    build_kulonbsegek_egyezesek()

    # 4. Normalizált címek párosítása
    print("\n4. címek párosítása...")
    build_parositas()

    print("\n5. Teljes normalizált egyezések keresése...")
    build_normalizalt_parositas()

    print("\n6. Szintenkénti címek párosítása...")
    build_szintenkenti_parositas()

    print("\n" + "=" * 60)
    print("A TELJES CÍMPÁROSÍTÁSI FOLYAMAT ELKÉSZÜLT")
    print("=" * 60)


if __name__ == "__main__":
    main()
