# Jabker Static API

Static JSON API berisi data **Jabatan Kerja Bidang Jasa Konstruksi** yang dipublish ke **GitHub Pages**.

Data bersumber dari [Direktorat Jenderal Bina Konstruksi](https://binakonstruksi.pu.go.id/dokumen-skkni/) berdasarkan **SK Dirjen Bina Konstruksi Nomor 33/KPTS/Dk/2023**.

---

## Endpoint

Setelah dipublish ke GitHub Pages, endpoint tersedia di:

```
https://<username>.github.io/<repo>/api/index.json
https://<username>.github.io/<repo>/api/klasifikasi.json
https://<username>.github.io/<repo>/api/metadata.json
```

---

## Struktur Data

### `api/index.json`
Array dari seluruh jabatan kerja:

```json
{
  "id": "arsitektur-asisten-arsitek-001",
  "klasifikasi": "Arsitektur",
  "subklasifikasi": "Arsitektural",
  "jabatan_kerja": "Asisten Arsitek",
  "jenjang": "Asisten Arsitek",
  "kualifikasi": "Ahli",
  "jenjang_kkni": "7",
  "standar_kompetensi_kerja": "SKKNI 196-2021",
  "link_skk": "https://skkni-api.kemnaker.go.id/...",
  "updated_at": "2026-03-08T00:10:00+07:00"
}
```

### `api/klasifikasi.json`
Ringkasan per klasifikasi:

```json
{
  "kode": "A",
  "nama": "Arsitektur",
  "jumlah_jabatan": 12
}
```

### `api/metadata.json`
Informasi build terakhir: total records, waktu generate, sumber, referensi SK.

---

## Klasifikasi

| Kode | Nama |
|------|------|
| A | Arsitektur |
| B | Sipil |
| C | Mekanikal |
| D | Tata Lingkungan |
| E | Manajemen Pelaksanaan |
| F | Arsitektur Lanskap, Iluminasi dan Desain Interior |
| G | Perencanaan Wilayah dan Kota |
| H | Sains dan Rekayasa Teknik |

---

## Setup & Penggunaan

### Jalankan lokal

```bash
pip install -r requirements.txt
python build.py
```

Output JSON akan tersimpan di folder `api/`.

### Setup GitHub Pages

1. Push repository ke GitHub.
2. Buka **Settings → Pages**.
3. Set source: `Deploy from a branch`, branch: `main`, folder: `/ (root)`.
4. Akses endpoint di `https://<username>.github.io/<repo>/api/index.json`.

### Update otomatis

GitHub Actions (`update-data.yml`) sudah dikonfigurasi untuk berjalan **setiap Senin pukul 01:00 WIB** secara otomatis, atau dapat dijalankan manual dari tab **Actions**.

---

## Konsumsi dari Laravel

```php
use Illuminate\Support\Facades\Http;

$jabker = Http::get('https://<username>.github.io/<repo>/api/index.json')->json();
```

Disarankan menyimpan hasil dengan `Cache::remember()` agar tidak fetch setiap request.
