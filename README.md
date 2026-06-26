# Olahin API Backend - Automated Preprocessing & Statistical Analysis

Backend modular berbasis FastAPI yang bertugas memproses file data secara otomatis melalui 5 pipeline utama, mendeteksi tipe data, menangani data kosong (imputasi/drop), mendeteksi outlier (IQR), melakukan pengujian normalitas, memilih uji statistik yang tepat (routing logika), menerjemahkan hasil menjadi narasi Bahasa Indonesia, serta menyajikan grafik visualisasi dan dokumen laporan (.docx).

---

## 📁 Struktur Proyek (Feature-Based Architecture)

Sistem ini didesain agar modular sehingga memudahkan Anda menambahkan fitur-fitur baru lainnya di masa depan. Fitur analisis statistik saat ini dibungkus sebagai satu fitur terpisah bernama `statistical_analysis`.

```
be-olahin/
├── app/
│   ├── __init__.py
│   ├── main.py                          # Entry point aplikasi FastAPI
│   ├── config.py                        # Konfigurasi direktori penyimpanan data & laporan
│   └── features/
│       ├── __init__.py
│       └── statistical_analysis/        # Fitur Utama: Analisis Statistik Otomatis
│           ├── __init__.py
│           ├── router.py                # Endpoint API (/upload, /analyze, /download)
│           ├── models.py                # Validasi Pydantic Schema
│           └── pipelines/
│               ├── __init__.py
│               ├── ingestion.py          # Pipeline 1: Ingestion & Validasi Ekstensi (.csv, .xlsx, .xls)
│               ├── preprocessing.py      # Pipeline 2: Pembersihan Data (Tipe data, Imputasi, Outlier)
│               ├── statistics.py         # Pipeline 3: Uji Normalitas & Routing Keputusan Otomatis
│               ├── interpretation.py     # Pipeline 4: Narasi Bahasa Indonesia Dinamis
│               └── visualization.py      # Pipeline 5: Base64 Chart & Pembuatan Laporan Word (.docx)
├── data/                                # Direktori data (dibuat otomatis)
│   ├── raw/                             # Tempat file mentah yang diunggah disimpan
│   └── exports/                         # Tempat laporan .docx hasil analisis disimpan
├── requirements.txt                     # Keterangan dependensi library
└── README.md                            # Dokumentasi teknis proyek
```

---

## 🚀 Panduan Memulai & Instalasi

### 1. Prasyarat
Pastikan sistem Anda sudah terinstal Python versi 3.10 ke atas (Sistem ini diverifikasi menggunakan Python 3.12.2).

### 2. Setup Virtual Environment
Buka terminal/Command Prompt di folder `be-olahin/` lalu jalankan perintah berikut:

**Windows PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependensi
Jalankan perintah berikut untuk menginstal semua library pendukung:
```bash
pip install -r requirements.txt
```

### 4. Menjalankan Server API
Jalankan server pengembangan FastAPI menggunakan uvicorn:
```bash
uvicorn app.main:app --reload
```
Server akan berjalan secara lokal di alamat: `http://127.0.0.1:8000`.
- **Swagger UI (Uji Interaktif)**: Buka browser Anda dan akses `http://127.0.0.1:8000/docs` untuk menggunakan interface pengujian endpoint.

---

## ⚙️ Cara Kerja 5 Pipeline Utama

1. **Pipeline 1: Data Ingestion & Validation** (`ingestion.py`)
   - Menerima file data melalui FastAPI `UploadFile`.
   - Memvalidasi bahwa file bertipe `.csv`, `.xlsx`, atau `.xls`.
   - Membaca file menggunakan Pandas dengan engine yang sesuai (`openpyxl` untuk XLSX, `xlrd` untuk XLS).
   - Menyimpan file ke `data/raw/` dengan nama unik (UUID) untuk referensi sesi berikutnya.
   - Mengembalikan informasi awal: daftar nama kolom, tipe kolom terdeteksi, total baris ($N$), dan total kolom.

2. **Pipeline 2: Automated Preprocessing Engine** (`preprocessing.py`)
   - Mengambil data asli berdasarkan `file_id`.
   - Melakukan inferensi tipe data dinamis.
   - Menghitung persentase data kosong (NaN) khusus kolom yang dianalisis:
     - Jika persentase data kosong $< 5\%$, baris data kosong langsung dihapus (`drop`).
     - Jika persentase data kosong $\ge 5\%$, sistem mengimputasi data kosong: numerik diisi dengan nilai **Median**, kategorikal diisi dengan **Modus**.
   - Menyaring outlier menggunakan metode **Interquartile Range (IQR)** dengan batas $Q1 - 1.5 \times IQR$ dan $Q3 + 1.5 \times IQR$.

3. **Pipeline 3: Statistical Inference & Decision Routing** (`statistics.py`)
   - Menguji apakah data berdistribusi normal menggunakan Uji Normalitas Otomatis:
     - Jika $N < 50$ baris, sistem mengeksekusi uji **Shapiro-Wilk**.
     - Jika $N \ge 50$ baris, sistem mengeksekusi uji **Kolmogorov-Smirnov**.
   - Melakukan routing logika:
     - **Kondisi A (Asosiatif & Normal \u2265 0.05)** $\rightarrow$ **Regresi Linear Berganda** (Parametrik OLS).
     - **Kondisi B (Asosiatif & Tidak Normal < 0.05)** $\rightarrow$ **Korelasi Spearman Rank** (Non-Parametrik).
     - **Kondisi C (Komparatif & Normal \u2265 0.05)** $\rightarrow$ **Independent Samples T-Test** (Parametrik).
     - **Kondisi D (Komparatif & Tidak Normal < 0.05)** $\rightarrow$ **Mann-Whitney U Test** (Non-Parametrik).

4. **Pipeline 4: Natural Language Interpretation** (`interpretation.py`)
   - Menerjemahkan output perhitungan rumus statistika menjadi bahasa Indonesia yang luwes dan akademis.
   - Menerapkan aturan pengujian hipotesis: jika p-value utama $< 0.05$, hipotesis (H1) Diterima (terdapat pengaruh/perbedaan/hubungan yang signifikan).
   - Menghitung persentase kontribusi $R^2$ (untuk Regresi) dan kekuatan hubungan (untuk Spearman).

5. **Pipeline 5: Visualization & Export Gate** (`visualization.py`)
   - Menggambar grafik berkualitas tinggi menggunakan Seaborn/Matplotlib secara otomatis:
     - Uji Asosiatif (Regresi/Spearman): **Scatter Plot** lengkap dengan garis tren linear.
     - Uji Komparatif (T-Test/Mann-Whitney): **Box Plot** yang memperlihatkan distribusi nilai kelompok.
   - Mengonversi plot menjadi representasi string Base64 agar dapat ditampilkan secara real-time di UI web/mobile.
   - Menyusun dokumen laporan format Microsoft Word (`.docx`) menggunakan template yang rapi dan memuat tabel hasil uji statistik, narasi interpretasi, serta gambar visualisasi grafik yang siap diunduh.

---

## 🧪 Jalankan Script Verifikasi Otomatis
Kami telah menyediakan script verifikasi mandiri di folder `C:\Users\MSI Modern\.gemini\antigravity\brain\c20c73da-3819-4fd0-90b1-41074426a37b\scratch\verify_pipelines.py` yang dapat Anda jalankan untuk memverifikasi kebenaran matematika, routing statistik, pengolahan data kosong, dan pembuatan file laporan Word secara langsung tanpa harus menyalakan server API.

Cara menjalankan:
```bash
python "C:\Users\MSI Modern\.gemini\antigravity\brain\c20c73da-3819-4fd0-90b1-41074426a37b\scratch\verify_pipelines.py"
```
Jika sukses, semua test case akan mencetak log keberhasilan dan akan menghasilkan file laporan uji coba di direktori `be-olahin/data/exports/`.
