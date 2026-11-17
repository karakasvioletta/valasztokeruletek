# Magyarországi választókerületi és szavazóköri adatok feldolgozása

A projekt célja a magyarországi országgyűlési választások választókerületi, szavazóköri és címadatainak letöltése, feldolgozása és összehasonlítása.

A program elsősorban a **2022-es és 2026-os választási adatok összehasonlítására**, valamint a két év között megváltozott, megszűnt vagy újonnan megjelenő szavazóköri címek azonosítására szolgál.

## Főbb funkciók

- Hivatalos választási adatok automatikus letöltése és feldolgozása.
- A 2010-es, 2014-es, 2022-es és 2026-os adatok összegyűjtése.
- A 2022-es és 2026-os választási adatok egységesítése és előkészítése.
- Megyei, települési és szavazóköri referencia-táblák létrehozása.
- A két év szavazóköri címeinek összehasonlítása.
- Címek párosítása több egyezési szint alapján.
- A nem teljesen egyező címek normalizálása és további vizsgálata.
- A párosítatlan és kétértelmű címek különálló táblákba rendezése.

## A projekt felépítése

```text
valasztokeruletek/
│
├── data/
│   ├── raw/
│   │   └── Letöltött nyers adatok
│   │
│   └── processed/
│       ├── reference_tables/
│       ├── matches/
│       ├── differences/
│       └── comparison/
│
├── scripts/
│   ├── alap_tablak/
│   ├── alap_parositas/
│   ├── kulonbsegek_szintenkent/
│   ├── normalizalt_egyezesek/
│   └── szintenkenti_egyezesek/
│
├── config.py
├── download_data.py
├── build_reference_tables.py
├── finding_matches.py
├── main.py
├── requirements.txt
└── README.md
```

### Főbb fájlok

| Fájl | Feladat |
|---|---|
| `config.py` | Projektútvonalak, adatkönyvtárak és fájlnevek központi beállítása |
| `download_data.py` | Választási adatok letöltése és nyers CSV-fájlok előállítása |
| `build_reference_tables.py` | Megyei, települési és szavazóköri referencia-táblák létrehozása |
| `finding_matches.py` | A teljes cím-összehasonlítási és párosítási folyamat vezérlése |
| `main.py` | A teljes adatfeldolgozási folyamat központi belépési pontja |

## A feldolgozás menete

### 1. Adatok letöltése

A `download_data.py` a hivatalos választási adatforrásokból letölti és feldolgozza a 2010-es, 2014-es, 2022-es és 2026-os adatokat.

Az eredményül kapott nyers CSV-fájlok a `data/raw/` könyvtárba kerülnek.

A már meglévő éves adatfájlokat a program nem tölti le újra.

### 2. Referencia-táblák előállítása

A `build_reference_tables.py` feldolgozza a 2022-es és 2026-os adatokat, és előállítja a további elemzésekhez szükséges referencia-táblákat.

### 3. Címek összehasonlítása és párosítása

A `finding_matches.py` vezérli a címek összehasonlításának teljes folyamatát.

A feldolgozás főbb lépései:

1. Alapvető címek párosítása.
2. Különbségek vizsgálata település, PIR és közterület szintjén.
3. Az egyező települések, PIR-ek és közterületek kiválasztása.
4. Címek további párosítása.
5. Normalizált címek egyezéseinek keresése.
6. A fennmaradó címek párosítása több különböző egyezési szint alapján.

A folyamat során a program külön kezeli a többszörös kulcsokat, a kétértelmű címeket és a párosítatlan rekordokat.

## Telepítés

A projekt Python környezetben futtatható.

A repository klónozása:

```bash
git clone https://github.com/karakasvioletta/valasztokeruletek.git
cd valasztokeruletek
```

Virtuális környezet létrehozása:

```bash
python -m venv .venv
```

Aktiválás Linux rendszeren:

```bash
source .venv/bin/activate
```

A szükséges csomagok telepítése:

```bash
pip install -r requirements.txt
```

## Futtatás

A feldolgozási lépések külön-külön is futtathatók.

```bash
python download_data.py
```

```bash
python build_reference_tables.py
```

```bash
python finding_matches.py
```

A következő lépés csak az előző sikeres lefutása után indítandó.

## Adatok és kimenetek

A nyers és feldolgozott adatfájlok a `data/` könyvtárban találhatók.

- `data/raw/`: letöltött nyers választási adatok.
- `data/processed/reference_tables/`: referencia-táblák.
- `data/processed/matches/`: alapvető cím-párosítások eredményei.
- `data/processed/differences/`: különbségvizsgálatok eredményei.
- `data/processed/comparison/`: további összehasonlítások és párosítások eredményei.

A `data/` könyvtár és az adatfájlok nem részei a Git repositorynak; a `.gitignore` kizárja őket. A szükséges adatok a letöltőprogrammal állíthatók elő.

## Felhasznált technológiák

- Python
- pandas
- requests
- BeautifulSoup

## Adatforrások

A projekt a magyarországi választási adatok hivatalos közzétételi felületeit használja:

- [Nemzeti Választási Iroda](https://www.valasztas.hu/)
- [2010-es választási adatok](https://static.valasztas.hu/dyn/pv10vt/vertaj-static/pv10vt/telkiv-ur1-cha.html)
- [2014-es választási adatok](https://static.valasztas.hu/dyn/pv14/vertaj/hu/v2.html)

A 2022-es és 2026-os adatok a Nemzeti Választási Iroda letölthető adatállományaiból származnak.

---

A projekt fejlesztés alatt áll. Az adatfeldolgozási és párosítási folyamatok folyamatosan bővülnek és finomodnak.