# Praktikum Keamanan Database — SQL Injection
**Repository**: DatabaseSecurity_0052 | **Mata Kuliah**: Keamanan Siber

---

## Apa yang dipelajari?

Di praktikum ini kita mencoba menyerang sebuah website Flask sederhana menggunakan dua teknik SQL Injection yang umum, yaitu **Tautology** dan **Piggyback**. Setelah berhasil menyerang, kita perbaiki kodenya supaya serangan tersebut tidak bisa dilakukan lagi.

---

## File yang ada di repository ini

- `web01_original.py` — kode asli yang masih punya celah keamanan
- `web01.py` — kode yang sudah diperbaiki dan aman
- `README.md` — dokumentasi ini

---

## Serangan 1: Tautology Attack

### Apa itu tautology?

Tautology berarti kita menyisipkan kondisi yang **selalu benar** ke dalam query SQL, sehingga sistem mengira kita sudah login dengan benar padahal belum.

### Kenapa bisa terjadi?

Karena kode di `web01_original.py` langsung menempelkan input user ke dalam query SQL tanpa filter:

```python
cur.execute(
    "SELECT id, username FROM `user` WHERE username='%s' AND password='%s'"
    % (username, password)
)
```

### Cara menyerangnya

Masukkan ini di kolom username saat login:
- **Username**: `user1' OR '1'='1`
- **Password**: `123` (isi bebas, tidak berpengaruh)

Query yang terbentuk di database jadi seperti ini:

```sql
SELECT id, username FROM user 
WHERE username='user1' OR '1'='1' AND password='123'
```

Karena `'1'='1'` selalu benar, sistem langsung mengizinkan masuk tanpa cek password.

### Hasilnya — Serangan Berhasil

![Hasil Tautology Berhasil](hasil%20original.png)

Kita berhasil masuk sebagai **user1** padahal password yang dimasukkan salah. Di terminal terlihat `POST /login HTTP/1.1" 302` yang artinya login berhasil dan diarahkan ke halaman utama.

---

## Serangan 2: Piggyback Attack

### Apa itu piggyback?

Piggyback berarti kita "menumpangkan" perintah SQL berbahaya di belakang perintah yang normal. Misalnya setelah INSERT data, kita selipkan perintah DELETE untuk menghapus data orang lain.

### Kenapa bisa terjadi?

Kode asli menggunakan `executescript()` yang memperbolehkan beberapa perintah SQL sekaligus dipisah tanda titik koma:

```python
cur.executescript(
    "INSERT INTO `time_line` VALUES (NULL, %d, '%s')" % (uid, content)
)
```

### Cara menyerangnya

Setelah login normal sebagai `user1`, isi form tambah timeline dengan payload ini:

data'); DELETE FROM time_line WHERE (content='World

Query yang terbentuk jadi dua perintah sekaligus:

```sql
INSERT INTO time_line VALUES (NULL, 1, 'data');
DELETE FROM time_line WHERE (content='World')
```

### Hasilnya — Serangan Berhasil

![Setelah Hapus Data World](setelah%20hapus%20data%20world.png)

Data **"World"** berhasil dihapus dari database, padahal kita hanya mengisi form tambah timeline biasa.

---

## Perbaikan: Mencegah SQL Injection

Solusi utamanya adalah menggunakan **Parameterized Query** — yaitu memisahkan struktur SQL dari data yang dimasukkan user. Dengan cara ini, karakter berbahaya seperti tanda kutip `'` atau titik koma `;` tidak akan diproses sebagai bagian dari perintah SQL.

### Perbaikan login (mencegah tautology)

```python
# Sebelum — berbahaya
cur.execute(
    "SELECT id, username FROM `user` WHERE username='%s' AND password='%s'"
    % (username, password)
)

# Sesudah — aman
cur.execute(
    'SELECT id, username FROM `user` WHERE username=? AND password=?',
    (username, password)
)
```

### Perbaikan tambah timeline (mencegah piggyback)

```python
# Sebelum — berbahaya
cur.executescript(
    "INSERT INTO `time_line` VALUES (NULL, %d, '%s')" % (uid, content)
)

# Sesudah — aman
cur.execute(
    'INSERT INTO `time_line` VALUES (NULL, ?, ?)',
    (int(uid), content)
)
```

Perubahan kecil tapi dampaknya besar:
- `%s` diganti dengan `?` sebagai placeholder
- `executescript()` diganti dengan `execute()` supaya hanya satu perintah yang bisa dijalankan

### Tampilan kode yang sudah diperbaiki

![Full Code](full%20code.png)

### Hasilnya setelah diperbaiki

![Hasil Secure](hasil%20secure.png)

Payload yang sama dicoba lagi di versi aman, hasilnya **"Username/password salah"** — serangan tidak berhasil. Di terminal terlihat `POST /login HTTP/1.1" 200` yang artinya halaman login tetap ditampilkan, bukan diarahkan ke dalam.

---

## Perbandingan hasil

| Serangan | Versi | Hasil |
|---|---|---|
| Tautology `user1' OR '1'='1` | `web01_original.py` | Berhasil masuk tanpa password benar |
| Piggyback `data'); DELETE FROM...` | `web01_original.py` | Data "World" terhapus |
| Tautology `user1' OR '1'='1` | `web01.py` (aman) | Ditolak — login gagal |
| Piggyback `data'); DELETE FROM...` | `web01.py` (aman) | Ditolak — data tetap aman |

---

## Kesimpulan

SQL Injection terjadi karena input dari user langsung digabungkan ke dalam query SQL tanpa pengamanan. Cara paling efektif untuk mencegahnya:

1. Gunakan **Parameterized Query** — pakai `?` bukan `%s`
2. Pakai `execute()` bukan `executescript()` supaya tidak bisa menjalankan banyak perintah sekaligus
3. Selalu validasi tipe data, misalnya pastikan ID adalah angka dengan `int()`
4. Jangan hardcode secret key — gunakan `secrets.token_hex(32)`
