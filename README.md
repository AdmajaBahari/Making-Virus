# Timeline App — Praktikum Keamanan Siber

Web app sederhana yang sengaja vulnerable untuk demo serangan siber.

## Struktur File

```
timeline_app/
├── web.py              ← Flask server + integrasi virus
├── virus.py            ← Self-replicating Python virus
├── templates/
│   ├── index.html      ← UI utama (XSS vulnerable, notifikasi, disable click)
│   └── login.html      ← Halaman login
└── timeline.db         ← Database SQLite (auto-generated)
```

## Cara Menjalankan

```bash
pip install flask
python web.py
# Buka: http://127.0.0.1:5000
# Login: admin / admin123
```

## Vulnerabilities yang Ada (untuk demo)

| # | Jenis | Lokasi | Cara Exploit |
|---|-------|--------|-------------|
| 1 | **Stored XSS** | Form "Post Something" | Post: `<script>window.location='/?status=infected'</script>` |
| 2 | **SQL Injection** | Form Login | Username: `admin'--` |
| 3 | **Self-Replicating Virus** | virus.py | Dipanggil saat `?status=infected` |

## Alur Serangan (Stored XSS → Virus)

```
1. Attacker buka http://127.0.0.1:5000
2. Login sebagai admin / admin123
3. Di form "Post Something", ketik:
      <script>window.location='/?status=infected'</script>
4. Klik Add → payload tersimpan di database

5. Setiap user yang buka halaman:
   → script XSS dieksekusi
   → Redirect ke /?status=infected
   → [Browser] alert() muncul: "YOU HAVE BEEN INFECTED HAHAHA 💀"
   → [Browser] semua klik di-disable (pointerEvents: none)
   → [Browser] overlay merah muncul
   → [Server Console] print: "ANDA TELAH TERINFEKSI HAHAHA !!!"
   → [Server] virus.py dijalankan → menyebar ke semua .py di folder
```

## Cara Kerja virus.py

```
virus.py membaca dirinya sendiri (antara header dan footer marker)
→ Cari semua file *.py dan *.pyw di folder yang sama
→ Cek apakah sudah terinfeksi (ada marker "# VIRUS SAYS HI!")
→ Jika belum: sisipkan kode virus di bagian ATAS file tersebut
→ Print: "ANDA TELAH TERINFEKSI HAHAHA !!!"
```

> ⚠️ **PERINGATAN**: Hanya untuk lingkungan lokal / lab praktikum.
> Jangan deploy ke server publik!