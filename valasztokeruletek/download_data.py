import io
import re
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import RAW_DATA_DIR, FILE_2022, FILE_2026


OUT = RAW_DATA_DIR
ERROR_LOG = OUT / "hibak.txt"

URL_2010 = (
    "https://static.valasztas.hu/dyn/pv10vt/"
    "vertaj-static/pv10vt/telkiv-ur1-cha.html"
)
BASE_2014 = "https://static.valasztas.hu/dyn/pv14/vertaj/hu/"
URL_2014 = urljoin(BASE_2014, "v2.html")
URL_2022_PAGE = (
    "https://www.valasztas.hu/"
    "ogy2022-letoltheto-es-tovabbfeldolgozhato-adatok"
)
URL_2022_ZIP = (
    "https://portal-api.valasztas.hu/files/"
    "69280ae39718b8000287a073/"
    "korzetallomanyok_megyei_bontasban.zip.bin"
)
URL_2026_PAGE = (
    "https://www.valasztas.hu/"
    "ogy2026-letoltheto-es-tovabbfeldolgozhato-adatok"
)

S = requests.Session()
S.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
    )
})


def log(message):
    print(message)


def log_error(message):
    print("HIBA:", message)
    OUT.mkdir(parents=True, exist_ok=True)
    with ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def get_bytes(url, attempts=4):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = S.get(url, timeout=60)
            response.raise_for_status()
            if not response.content:
                raise ValueError("Üres válasz érkezett.")
            return response.content
        except Exception as exc:
            last_error = exc
            log(f"  Letöltési hiba ({attempt}/{attempts}): {url}\n    {exc}")
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Nem sikerült letölteni: {url}; {last_error}")


def get_soup(url):
    return BeautifulSoup(get_bytes(url), "html.parser")


def txt(element):
    return re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()


def save_csv(df, filename):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    df.fillna("").to_csv(path, index=False, encoding="utf-8-sig")
    log(f"Mentve: {path} ({len(df)} sor, {len(df.columns)} oszlop)")


def expand_html_table(table):
    """HTML-tábla kiterítése rowspan/colspan figyelembevételével."""
    output = []
    spans = {}

    for tr in table.find_all("tr"):
        row = []
        next_spans = {}
        col = 0

        cells = tr.find_all(["td", "th"], recursive=False)
        for cell in cells:
            while col in spans:
                value, remaining = spans[col]
                row.append(value)
                if remaining > 1:
                    next_spans[col] = (value, remaining - 1)
                col += 1

            value = txt(cell)
            try:
                colspan = max(1, int(cell.get("colspan", 1)))
            except (ValueError, TypeError):
                colspan = 1
            try:
                rowspan = max(1, int(cell.get("rowspan", 1)))
            except (ValueError, TypeError):
                rowspan = 1

            for _ in range(colspan):
                row.append(value)
                if rowspan > 1:
                    next_spans[len(row) - 1] = (value, rowspan - 1)
                col += 1

        while col in spans:
            value, remaining = spans[col]
            row.append(value)
            if remaining > 1:
                next_spans[col] = (value, remaining - 1)
            col += 1

        if row:
            output.append(row)
        spans = next_spans

    if not output:
        return []

    width = max(map(len, output))
    return [row + [""] * (width - len(row)) for row in output]


def normalize_columns(columns):
    names = []
    counts = {}
    for i, value in enumerate(columns, 1):
        name = re.sub(r"\s+", " ", str(value or "")).strip()
        if not name or name.lower().startswith("unnamed"):
            name = f"Oszlop_{i}"
        counts[name] = counts.get(name, 0) + 1
        if counts[name] > 1:
            name = f"{name}_{counts[name]}"
        names.append(name)
    return names


def crawl_internal_links(start_url, base_prefix, max_pages=5000):
    """
    Korlátozott belső HTML-bejárás. Csak ugyanazon választási
    archívum URL-jeit követi, és a már meglátogatott URL-eket kihagyja.
    """
    queue = [start_url]
    visited = set()
    pages = {}

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            soup = get_soup(url)
            pages[url] = soup
        except Exception as exc:
            log_error(f"Oldal nem olvasható: {url} | {exc}")
            continue

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#")[0]
            parsed = urlparse(link)

            if parsed.scheme not in ("http", "https"):
                continue
            if not link.startswith(base_prefix):
                continue
            if not parsed.path.lower().endswith((".html", ".htm")):
                continue
            if link not in visited and link not in queue:
                queue.append(link)

        time.sleep(0.03)

    log(f"Belső HTML-oldalak feldolgozva: {len(pages)}")
    return pages


# ------------------------------------------------------------------
# 2010
# ------------------------------------------------------------------

def is_2010_data_row(row):
    values = [re.sub(r"\s+", "", str(v)) for v in row]
    # Az ismert táblaszerkezetben a szavazókör a 9., az OEVK a 10. mező.
    if len(values) > 9 and re.fullmatch(r"\d{3}", values[8]) and \
            re.fullmatch(r"\d{2}", values[9]):
        return True
    # Tartalék keresés a sor utolsó mezői körül.
    for i in range(max(0, len(values) - 6), len(values) - 1):
        if re.fullmatch(r"\d{3}", values[i]) and \
                re.fullmatch(r"\d{2}", values[i + 1]):
            return True
    return False


def discover_2010_cities():
    log("\n2010: településoldalak felderítése")
    soup = get_soup(URL_2010)
    letter_urls = {URL_2010}

    for a in soup.find_all("a", href=True):
        url = urljoin(URL_2010, a["href"])
        name = urlparse(url).path.rsplit("/", 1)[-1].lower()
        if "static.valasztas.hu" in url and "pv10vt" in url and \
                "telkiv-ur1-" in name and name.endswith(".html"):
            letter_urls.add(url)

    cities = {}
    for letter_url in sorted(letter_urls):
        try:
            letter_soup = get_soup(letter_url)
            for a in letter_soup.find_all("a", href=True):
                url = urljoin(letter_url, a["href"])
                path = urlparse(url).path
                if "static.valasztas.hu" in url and "pv10vt" in path and \
                        re.search(r"/taz/.*/v21\.html$", path, re.I):
                    cities[url] = txt(a) or "Ismeretlen település"
        except Exception as exc:
            log_error(f"2010 betűoldalhiba: {letter_url} | {exc}")

    # Külön újrapróbálkozás a korábban kimaradt településekre.
    cities.update({
        "https://static.valasztas.hu/dyn/pv10vt/vertaj-static/pv10vt/maz/09/taz/079/v21.html": "Vámospércs",
        "https://static.valasztas.hu/dyn/pv10vt/vertaj-static/pv10vt/maz/08/taz/172/v21.html": "Vámosszabadi",
        "https://static.valasztas.hu/dyn/pv10vt/vertaj-static/pv10vt/maz/05/taz/346/v21.html": "Vámosújfalu",
    })
    return cities


def scrape_2010_city(name, v21_url):
    soup = get_soup(v21_url)
    v22_url = None

    for a in soup.find_all("a", href=True):
        label = txt(a).casefold()
        if "körzetadatok" in label and "közterületek" in label:
            v22_url = urljoin(v21_url, a["href"])
            break

    if not v22_url:
        v22_url = re.sub(r"v21\.html(?:\?.*)?$", "v22.html", v21_url, flags=re.I)

    soup22 = get_soup(v22_url)
    candidates = []

    for table in soup22.find_all("table"):
        rows = expand_html_table(table)
        data = [r for r in rows if is_2010_data_row(r)]
        if data:
            candidates.append((len(data), rows, data))

    if not candidates:
        raise ValueError("Nem találtam körzetadatokat a v22 oldalon.")

    _, _, data = max(candidates, key=lambda x: x[0])

    # Minden adatsort pontosan 11 mezőre igazítunk.
    # Ez biztosítja, hogy a 2010-es oszlopok megfeleljenek
    # a 2014-es adatok oszlopszerkezetének.
    data = [
        (row + [""] * len(COLS_2014))[:len(COLS_2014)]
        for row in data
    ]

    # A 2014-es adatokkal megegyező oszlopnevek használata.
    df = pd.DataFrame(data, columns=COLS_2014)

    # Metaadatok hozzáadása, a 2014-es oszlopsorrenddel megegyezően.
    df.insert(0, "Település", name)
    df.insert(0, "Megye", "")
    df["Forrás URL"] = v22_url
    df["Év"] = "2010"

    return df


def scrape_2010():
    log("\n" + "=" * 55 + "\n2010-ES ADATOK\n" + "=" * 55)
    cities = discover_2010_cities()
    results = []

    for i, (url, name) in enumerate(sorted(cities.items()), 1):
        log(f"[2010 {i}/{len(cities)}] {name}")
        success = False
        for attempt in range(1, 4):
            try:
                df = scrape_2010_city(name, url)
                results.append(df)
                log(f"  OK: {len(df)} sor")
                success = True
                break
            except Exception as exc:
                log(f"  Próbálkozás {attempt}/3 sikertelen: {exc}")
                if attempt < 3:
                    time.sleep(attempt * 2)
        if not success:
            log_error(f"2010 | {name} | {url} | sikertelen 3 próbálkozás")
        time.sleep(0.1)

    if not results:
        raise RuntimeError("A 2010-es letöltésből nem lett adat.")

    df = pd.concat(results, ignore_index=True, sort=False).drop_duplicates()
    save_csv(df, "2010_korzetadatok.csv")
    return df


# ------------------------------------------------------------------
# 2014
# ------------------------------------------------------------------

COLS_2014 = [
    "Közterület neve és jellege",
    "Kezdő házszám",
    "Kezdő épü.",
    "Kezdő Lph.",
    "Vég házszám",
    "Vég épü.",
    "Vég Lph.",
    "Tartomány típusa",
    "Szavazókör",
    "OEVK",
    "Címe",
]

MEGYE_KODOK_2014 = {
    "M01": "Budapest",
    "M02": "Baranya",
    "M03": "Bács-Kiskun",
    "M04": "Békés",
    "M05": "Borsod-Abaúj-Zemplén",
    "M06": "Csongrád",
    "M07": "Fejér",
    "M08": "Győr-Moson-Sopron",
    "M09": "Hajdú-Bihar",
    "M10": "Heves",
    "M11": "Jász-Nagykun-Szolnok",
    "M12": "Komárom-Esztergom",
    "M13": "Nógrád",
    "M14": "Pest",
    "M15": "Somogy",
    "M16": "Szabolcs-Szatmár-Bereg",
    "M17": "Tolna",
    "M18": "Vas",
    "M19": "Veszprém",
    "M20": "Zala",
}

def discover_2014_cities():
    """
    A 2014-es v2.html indexből kiindulva bejárja a régi választási
    portál belső HTML-oldalait, és megkeresi a Txxx/v21.html
    települési oldalakat.
    """
    log("\n2014: településoldalak felderítése")
    pages = crawl_internal_links(URL_2014, BASE_2014, max_pages=5000)
    cities = {}

    for page_url, soup in pages.items():
        for a in soup.find_all("a", href=True):
            url = urljoin(page_url, a["href"]).split("#")[0]
            path = urlparse(url).path
            if not url.startswith(BASE_2014):
                continue
            if re.search(r"/T\d{3}/v21\.html$", path, re.I):
                name = txt(a) or "Ismeretlen település"
                cities[url] = name

    # Ha a települési v21 link egy köztes indexben szerepel,
    # a crawler a linket is eléri, így a településlistát összegyűjti.
    log(f"2014-es településoldalak: {len(cities)}")
    return cities


def scrape_2014_city(name, v21_url):
    # Megye kinyerése a településoldal URL-jéből
    match = re.search(r"/(M\d{2})/T\d{3}/v21\.html$", v21_url, re.I)

    if not match:
        raise ValueError(
            f"Nem sikerült kinyerni a megye kódját az URL-ből: {v21_url}"
        )

    megye_kod = match.group(1).upper()
    megye = MEGYE_KODOK_2014.get(megye_kod)

    if megye is None:
        raise ValueError(
            f"Ismeretlen megyei kód: {megye_kod} | URL: {v21_url}"
        )

    soup = get_soup(v21_url)
    v22_url = None

    for a in soup.find_all("a", href=True):
        label = txt(a).casefold()
        if "körzetadatok" in label and "közterületek" in label:
            v22_url = urljoin(v21_url, a["href"])
            break

    if not v22_url:
        v22_url = re.sub(r"v21\.html(?:\?.*)?$", "v22.html", v21_url, flags=re.I)

    soup22 = get_soup(v22_url)
    tables = []

    for table in soup22.find_all("table"):
        rows = expand_html_table(table)
        if len(rows) < 2:
            continue

        # A fejléc vagy az első adatsor körül keressük a 11 oszlopos táblát.
        if max(map(len, rows)) >= 11:
            tables.append(rows)

    if not tables:
        raise ValueError("Nem találtam feldolgozható közterületi táblát.")

    rows = max(tables, key=len)

    # A régi portál táblájában a 11 oszlop jellemzően a fejléc után jön.
    data = []
    for row in rows:
        row = (row + [""] * 11)[:11]
        joined = " ".join(row).casefold()
        if "közterület" in joined and "szavazókör" in joined:
            continue
        if not any(str(v).strip() for v in row):
            continue
        data.append(row)

    # A fejlécsorokat eltávolítjuk, de csak ha valóban fejlécnek tűnnek.
    cleaned = []
    for row in data:
        if any("közterület neve" in str(v).casefold() for v in row):
            continue
        cleaned.append(row)

    if not cleaned:
        raise ValueError("A táblában nem maradt adatsor.")

    df = pd.DataFrame(cleaned, columns=COLS_2014)

    df.insert(0, "Település", name)
    df.insert(0, "Megye", megye)

    df["Forrás URL"] = v22_url
    df["Év"] = "2014"

    return df


def scrape_2014():
    log("\n" + "=" * 55 + "\n2014-ES ADATOK\n" + "=" * 55)
    cities = discover_2014_cities()
    if not cities:
        raise RuntimeError(
            "A 2014-es településoldalakat nem sikerült megtalálni. "
            "Ellenőrizd a hálózati elérést vagy az archívum linkstruktúráját."
        )

    results = []
    for i, (url, name) in enumerate(sorted(cities.items()), 1):
        log(f"[2014 {i}/{len(cities)}] {name}")
        success = False
        for attempt in range(1, 4):
            try:
                df = scrape_2014_city(name, url)
                results.append(df)
                log(f"  OK: {len(df)} sor")
                success = True
                break
            except Exception as exc:
                log(f"  Próbálkozás {attempt}/3 sikertelen: {exc}")
                if attempt < 3:
                    time.sleep(attempt * 2)
        if not success:
            log_error(f"2014 | {name} | {url} | sikertelen 3 próbálkozás")
        time.sleep(0.1)

    if not results:
        raise RuntimeError("A 2014-es letöltésből nem lett adat.")

    df = pd.concat(results, ignore_index=True, sort=False).drop_duplicates()
    save_csv(df, "2014_korzetadatok.csv")
    return df


# ------------------------------------------------------------------
# 2022
# ------------------------------------------------------------------

def scrape_2022():
    log("\n" + "=" * 55 + "\n2022-ES ADATOK\n" + "=" * 55)
    # Ha az archívum már le van töltve, a helyi példányt használjuk.
    if Path(FILE_2022).exists():
        log(f"  A 2022-es forrásfájl már létezik, nem töltöm le újra: {FILE_2022}")
        content = Path(FILE_2022).read_bytes()
    else:
        # Az oldalt is lekérjük; az archívum hivatalos közvetlen URL-je ismert.
        get_soup(URL_2022_PAGE)
        content = get_bytes(URL_2022_ZIP)
        Path(FILE_2022).parent.mkdir(parents=True, exist_ok=True)
        Path(FILE_2022).write_bytes(content)
        log(f"  A 2022-es forrásfájl elmentve: {FILE_2022}")

    buffer = io.BytesIO(content)

    if not zipfile.is_zipfile(buffer):
        raise ValueError("A 2022-es .bin állomány nem ZIP-archívum.")

    results = []
    with zipfile.ZipFile(buffer) as zf:
        files = [
            n for n in zf.namelist()
            if n.lower().endswith((".xlsx", ".xls"))
            and not n.startswith("__MACOSX/")
        ]
        if not files:
            raise ValueError("Nem található XLS/XLSX a 2022-es archívumban.")

        for filename in files:
            log(f"  Excel feldolgozása: {filename}")
            try:
                sheets = pd.read_excel(
                    io.BytesIO(zf.read(filename)),
                    sheet_name=None,
                    dtype=str
                )
                for sheet_name, df in sheets.items():
                    if df.empty:
                        continue
                    df.columns = normalize_columns(df.columns)
                    df = df.fillna("")
                    df.insert(0, "Forrás munkalap", sheet_name)
                    df.insert(0, "Forrás fájl", filename)
                    df["Év"] = "2022"
                    results.append(df)
            except Exception as exc:
                log_error(f"2022 | {filename} | {exc}")

    if not results:
        raise RuntimeError("A 2022-es Excel-fájlokból nem sikerült adatot olvasni.")

    df = pd.concat(results, ignore_index=True, sort=False).fillna("").drop_duplicates()
    save_csv(df, "2022_korzetadatok.csv")
    return df


# ------------------------------------------------------------------
# 2026
# ------------------------------------------------------------------

def find_2026_zip_url():
    """A 2026-os országos körzetállomány közvetlen letöltési címe."""
    url = (
        "https://portal-data.valasztas.hu/files/"
        "69e0d66f866db60002314087/"
        "Korzet_allomany_orszagos.zip"
    )

    log("2026-os országos körzetállomány URL-je: " + url)
    return url




def read_csv_bytes(data, filename):
    import csv

    errors = []

    # A magyar választási CSV-kben gyakori a pontosvesszős elválasztás.
    # Először a szabályos idézőjeles feldolgozást próbáljuk.
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        for engine in ("c", "python"):
            try:
                df = pd.read_csv(
                    io.BytesIO(data),
                    dtype=str,
                    encoding=encoding,
                    sep=";",
                    engine=engine,
                    on_bad_lines="error",
                )
                log(
                    f"  CSV sikeresen beolvasva: {filename} "
                    f"(kódolás={encoding}, motor={engine}, "
                    f"sorok={len(df)}, oszlopok={len(df.columns)})"
                )
                return df.fillna("")

            except Exception as exc:
                errors.append(
                    f"{encoding}, {engine}: {exc}"
                )

    # Tartalék megoldás hibás idézőjelek esetére.
    # Ilyenkor az idézőjelek egyszerű karakterként kezelődnek.
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            df = pd.read_csv(
                io.BytesIO(data),
                dtype=str,
                encoding=encoding,
                sep=";",
                engine="python",
                quoting=csv.QUOTE_NONE,
                on_bad_lines="error",
            )

            log(
                f"  CSV beolvasva idézőjelek speciális kezelése nélkül: "
                f"{filename} ({len(df)} sor, {len(df.columns)} oszlop)"
            )
            return df.fillna("")

        except Exception as exc:
            errors.append(
                f"{encoding}, idézőjelek nélkül: {exc}"
            )

    raise ValueError(
        f"CSV-olvasási hiba ({filename}): "
        + " | ".join(errors)
    )



def read_csvs_from_zip(data, prefix=""):
    results = []
    buffer = io.BytesIO(data)
    if not zipfile.is_zipfile(buffer):
        return results

    with zipfile.ZipFile(buffer) as zf:
        for name in zf.namelist():
            if name.endswith("/") or name.startswith("__MACOSX/"):
                continue
            full_name = f"{prefix}/{name}" if prefix else name

            if name.lower().endswith(".csv"):
                try:
                    df = read_csv_bytes(zf.read(name), full_name)
                    df.columns = normalize_columns(df.columns)
                    df.insert(0, "Forrás fájl", full_name)
                    df["Év"] = "2026"
                    results.append(df)
                    log(f"  CSV feldolgozva: {full_name} ({len(df)} sor)")
                except Exception as exc:
                    log_error(f"2026 | CSV | {full_name} | {exc}")

            elif name.lower().endswith(".zip"):
                results.extend(read_csvs_from_zip(zf.read(name), full_name))

    return results


def scrape_2026():
    log("\n" + "=" * 55 + "\n2026-OS ADATOK\n" + "=" * 55)

    url = find_2026_zip_url()

    # Ha az archívum már le van töltve, a helyi példányt használjuk.
    if Path(FILE_2026).exists():
        log(f"  A 2026-os forrásfájl már létezik, nem töltöm le újra: {FILE_2026}")
        content = Path(FILE_2026).read_bytes()
        response_url = url
        response_status = "helyi fájl"
        response_content_type = "helyi fájl"
        response_disposition = Path(FILE_2026).name
    else:
        # A letöltés külön ellenőrzése.
        response = S.get(url, timeout=180)
        response.raise_for_status()
        content = response.content
        Path(FILE_2026).parent.mkdir(parents=True, exist_ok=True)
        Path(FILE_2026).write_bytes(content)
        log(f"  A 2026-os forrásfájl elmentve: {FILE_2026}")
        response_url = response.url
        response_status = response.status_code
        response_content_type = response.headers.get("Content-Type")
        response_disposition = response.headers.get("Content-Disposition", "nincs megadva")

    log(f"Végleges URL: {response_url}")
    log(f"HTTP státusz: {response_status}")
    log(f"Content-Type: {response_content_type}")
    log("Content-Disposition: " + response_disposition)
    log(f"Letöltött méret: {len(content):,} bájt")
    log(f"Első 32 bájt: {content[:32]!r}")

    if not content:
        raise ValueError("A letöltött fájl üres.")

    # Ellenőrizzük, hogy a letöltés valóban ZIP-archívum-e.
    buffer = io.BytesIO(content)

    if not zipfile.is_zipfile(buffer):
        preview = content[:500].decode("utf-8", errors="replace")

        raise ValueError(
            "A letöltött fájl nem ismerhető fel ZIP-archívumként.\n"
            f"URL: {response.url}\n"
            f"Content-Type: {response.headers.get('Content-Type')}\n"
            f"Első 500 karakter:\n{preview}"
        )

    log("A ZIP-archívum ellenőrzése sikeres.")

    results = read_csvs_from_zip(content)

    if not results:
        raise RuntimeError(
            "A ZIP-archívum megnyitható, de nem található benne "
            "feldolgozható CSV-fájl."
        )

    df = (
        pd.concat(results, ignore_index=True, sort=False)
        .fillna("")
        .drop_duplicates()
    )

    save_csv(df, "2026_korzetadatok.csv")

    return df


# ------------------------------------------------------------------
# ÖSSZESÍTÉS ÉS FUTTATÁS
# ------------------------------------------------------------------

def combine_years(year_data):
    available = []
    for year, df in year_data.items():
        if df is not None and not df.empty:
            df = df.copy()
            if "Év" not in df.columns:
                df["Év"] = str(year)
            available.append(df)

    if not available:
        raise RuntimeError("Egyik évből sem sikerült adatot kinyerni.")

    combined = pd.concat(available, ignore_index=True, sort=False).fillna("")
    save_csv(combined, "2010_2014_2022_2026_osszesitett.csv")
    return combined


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if ERROR_LOG.exists():
        ERROR_LOG.unlink()

    log("Letöltés és feldolgozás indul. A már elkészült éves CSV-ket kihagyjuk.")

    tasks = [
        ("2010", "2010_korzetadatok.csv", scrape_2010),
        ("2014", "2014_korzetadatok.csv", scrape_2014),
        ("2022", "2022_korzetadatok.csv", scrape_2022),
        ("2026", "2026_korzetadatok.csv", scrape_2026),
    ]

    for year, output_filename, task in tasks:
        output_path = OUT / output_filename
        if output_path.exists():
            log(f"\\n{year}: a kimeneti fájl már létezik, kihagyom: {output_path}")
            continue
        try:
            task()
        except Exception as exc:
            log_error(f"{year} | Teljes feldolgozási hiba | {exc}")

    log("\\nKész. Kimeneti mappa: " + str(OUT.resolve()))
    log("Ha valamelyik év kimaradt, ellenőrizd a hibak.txt fájlt.")


if __name__ == "__main__":
    main()  
