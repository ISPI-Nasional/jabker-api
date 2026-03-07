#!/usr/bin/env python3
"""
Jabker Static API Builder
Scrapes jabatan kerja bidang jasa konstruksi from binakonstruksi.pu.go.id
and generates static JSON files for GitHub Pages.
"""

import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

# Source URL
SOURCE_URL = "https://binakonstruksi.pu.go.id/dokumen-skkni/"

# Output directory
OUTPUT_DIR = "api"

# Timezone WIB (UTC+7)
TZ_WIB = timezone(timedelta(hours=7))

# Klasifikasi mapping by letter code
KLASIFIKASI_MAP = {
    "A": "Arsitektur",
    "B": "Sipil",
    "C": "Mekanikal",
    "D": "Tata Lingkungan",
    "E": "Manajemen Pelaksanaan",
    "F": "Arsitektur Lanskap, Iluminasi dan Desain Interior",
    "G": "Perencanaan Wilayah dan Kota",
    "H": "Sains dan Rekayasa Teknik",
}


def slugify(text: str) -> str:
    """Convert text to slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def clean(text: str) -> str:
    return " ".join(text.split())


def get_links(cell) -> list:
    """Extract unique href links from a cell."""
    seen = set()
    links = []
    for a in cell.find_all("a", href=True):
        href = a["href"].strip()
        if href and href not in seen:
            seen.add(href)
            links.append(href)
    return links


def parse_table(table, klasifikasi_code: str, klasifikasi_name: str):
    """
    Parse a single table and return list of records.

    Table row formats observed:
    - 8 cols: [no, subklas, jabatan_kerja, jenjang_jabker, kualifikasi, jenjang_kkni, standar, link]
    - 7 cols: [no, jabatan_kerja, jenjang_jabker, kualifikasi, jenjang_kkni, standar, link]
              (when subklasifikasi spans via rowspan from previous row)
    - 4 cols: [jenjang_jabker, jenjang_kkni, standar, link]
              (continuation row: same jabker, additional jenjang)
    """
    records = []
    rows = table.find_all("tr")
    current_subklasifikasi = ""
    last_record = None  # Track the last "main" record for continuation rows

    id_counter = {}

    def make_id(klas_name, jabker):
        slug_key = f"{slugify(klas_name)}-{slugify(jabker)}"
        id_counter[slug_key] = id_counter.get(slug_key, 0) + 1
        return f"{slug_key}-{id_counter[slug_key]:03d}"

    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        nc = len(cells)
        texts = [clean(c.get_text()) for c in cells]

        # Skip header rows
        if "JABATAN KERJA" in texts or "SUBKLASIFIKASI" in texts:
            continue

        if nc == 8:
            # Full row: [no, subklas, jabker, jenjang, kualifikasi, kkni, standar, link]
            no_text = texts[0]
            subklas_text = texts[1]
            jabker_text = texts[2]
            jenjang_text = texts[3]
            kualifikasi_text = texts[4]
            kkni_text = texts[5]
            standar_text = texts[6]
            link_cell = cells[7]
            standar_cell = cells[6]

            # If no jabker → This is a klasifikasi header row
            if subklas_text and not jabker_text:
                current_subklasifikasi = re.sub(
                    r"^Klasifikasi\s+", "", subklas_text, flags=re.IGNORECASE
                ).strip()
                last_record = None
                continue

            if not jabker_text:
                continue

            # Update subklasifikasi if provided
            if subklas_text:
                current_subklasifikasi = re.sub(
                    r"^Klasifikasi\s+", "", subklas_text, flags=re.IGNORECASE
                ).strip()

            links = get_links(link_cell) or get_links(standar_cell)
            link_skk = links[0] if links else ""

            record = {
                "id": make_id(klasifikasi_name, jabker_text),
                "klasifikasi": klasifikasi_name,
                "subklasifikasi": current_subklasifikasi,
                "jabatan_kerja": jabker_text,
                "jenjang": jenjang_text,
                "kualifikasi": kualifikasi_text,
                "jenjang_kkni": kkni_text,
                "standar_kompetensi_kerja": standar_text,
                "link_skk": link_skk,
                "updated_at": datetime.now(TZ_WIB).isoformat(),
            }
            records.append(record)
            last_record = record

        elif nc == 7:
            # Row without subklas column: [no, jabker, jenjang, kualifikasi, kkni, standar, link]
            jabker_text = texts[1]
            jenjang_text = texts[2]
            kualifikasi_text = texts[3]
            kkni_text = texts[4]
            standar_text = texts[5]
            link_cell = cells[6]
            standar_cell = cells[5]

            if not jabker_text:
                continue

            links = get_links(link_cell) or get_links(standar_cell)
            link_skk = links[0] if links else ""

            record = {
                "id": make_id(klasifikasi_name, jabker_text),
                "klasifikasi": klasifikasi_name,
                "subklasifikasi": current_subklasifikasi,
                "jabatan_kerja": jabker_text,
                "jenjang": jenjang_text,
                "kualifikasi": kualifikasi_text,
                "jenjang_kkni": kkni_text,
                "standar_kompetensi_kerja": standar_text,
                "link_skk": link_skk,
                "updated_at": datetime.now(TZ_WIB).isoformat(),
            }
            records.append(record)
            last_record = record

        elif nc == 4:
            # Continuation row for a multi-jenjang jabatan kerja:
            # [jenjang_jabker, jenjang_kkni, standar, link]
            if last_record is None:
                continue

            jenjang_text = texts[0]
            kkni_text = texts[1]
            standar_text = texts[2]
            link_cell = cells[3]
            standar_cell = cells[2]

            links = get_links(link_cell) or get_links(standar_cell)
            link_skk = links[0] if links else ""

            # Clone parent record with additional jenjang info
            jabker_text = last_record["jabatan_kerja"]
            record = {
                "id": make_id(klasifikasi_name, jabker_text),
                "klasifikasi": klasifikasi_name,
                "subklasifikasi": last_record["subklasifikasi"],
                "jabatan_kerja": jabker_text,
                "jenjang": jenjang_text,
                "kualifikasi": last_record["kualifikasi"],
                "jenjang_kkni": kkni_text,
                "standar_kompetensi_kerja": standar_text,
                "link_skk": link_skk,
                "updated_at": datetime.now(TZ_WIB).isoformat(),
            }
            records.append(record)
            # Do NOT update last_record here to allow chained continuations

        else:
            # Ignore other row formats (e.g., header-like)
            pass

    return records


def fetch_and_build():
    print(f"[+] Fetching data from: {SOURCE_URL}")
    headers = {"User-Agent": "Mozilla/5.0 (jabker-api-builder/1.0)"}
    resp = requests.get(SOURCE_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    tables = soup.find_all("table")
    print(f"[+] Found {len(tables)} tables.")

    all_records = []
    klasifikasi_list = []

    for i, table in enumerate(tables):
        # Detect klasifikasi code from the first data row
        rows = table.find_all("tr")
        kode = None
        for row in rows:
            cells = row.find_all(["td", "th"])
            if cells:
                first_text = clean(cells[0].get_text())
                if first_text in KLASIFIKASI_MAP:
                    kode = first_text
                    break

        klas_name = KLASIFIKASI_MAP.get(kode, f"Klasifikasi-{chr(65 + i)}")
        print(f"  [+] Parsing table {i}: {kode} - {klas_name}")

        records = parse_table(table, kode or chr(65 + i), klas_name)
        all_records.extend(records)

        klasifikasi_list.append({
            "kode": kode or chr(65 + i),
            "nama": klas_name,
            "jumlah_jabatan": len(records),
        })

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    now_str = datetime.now(TZ_WIB).isoformat()

    # Write index.json
    index_path = os.path.join(OUTPUT_DIR, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"[+] Written {len(all_records)} records to {index_path}")

    # Write klasifikasi.json
    klas_path = os.path.join(OUTPUT_DIR, "klasifikasi.json")
    with open(klas_path, "w", encoding="utf-8") as f:
        json.dump(klasifikasi_list, f, ensure_ascii=False, indent=2)
    print(f"[+] Written {len(klasifikasi_list)} klasifikasi to {klas_path}")

    # Write metadata.json
    meta = {
        "source": SOURCE_URL,
        "total_records": len(all_records),
        "total_klasifikasi": len(klasifikasi_list),
        "generated_at": now_str,
        "updated_at": now_str,
        "description": "Daftar Jabatan Kerja Bidang Jasa Konstruksi",
        "reference": "SK Dirjen Bina Konstruksi Nomor 33/KPTS/Dk/2023",
    }
    meta_path = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[+] Written metadata to {meta_path}")

    print(f"\n[✓] Done! {len(all_records)} jabatan kerja scraped.")
    return all_records


if __name__ == "__main__":
    fetch_and_build()
