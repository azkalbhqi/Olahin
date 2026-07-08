# Product Requirements Document (PRD): Research Companion (Recomp)

**Versi:** 2.1 (Revisi — disinkronkan dengan Systemflow.md v1.1)
**Status:** Draft for Review
**Terakhir diperbarui:** Juli 2026

---

## 1. Executive Summary

**Recomp (Research Companion)** — sebelumnya disebut StatFlow Automator — adalah platform backend berbasis API yang bertujuan mengotomatisasi alur kerja analisis data statistik secara *end-to-end*. Sistem ini mentransformasi data mentah (CSV/Excel) menjadi insight statistik yang valid dan terstruktur, dengan pemilihan metode uji yang sepenuhnya otomatis berdasarkan struktur data, tujuan analisis, dan hasil uji asumsi — tanpa memerlukan intervensi manual dari pengguna dalam menentukan metode statistik yang tepat.

Sistem mendukung tiga jalur analisis utama sesuai diagram alur keputusan:
1. **Time-Series Path** — uji stasioneritas dan model deret waktu.
2. **Cross-Sectional Comparative Path** — uji beda (komparasi) antar grup.
3. **Cross-Sectional Associative Path** — uji hubungan/pengaruh antar variabel (korelasi, regresi, mediasi/moderasi, SEM).

---

## 2. Problem Statement

Peneliti (mahasiswa, akademisi, analis) sering kesulitan menentukan uji statistik yang tepat karena harus memahami:
- Jenis data (numerik/kategorik, time-series/cross-sectional)
- Asumsi normalitas, homogenitas, stasioneritas
- Jumlah grup, status berpasangan/independen
- Tujuan analisis (komparasi, pengaruh, korelasi, mediasi)

Kesalahan pemilihan uji berakibat pada kesimpulan penelitian yang tidak valid. Recomp menghilangkan hambatan ini melalui *decision engine* otomatis.

---

## 3. User Roles

| Role | Deskripsi |
|---|---|
| **Researcher** | Pengguna yang mengunggah data untuk validasi hipotesis dan menerima laporan interpretasi. |
| **System Admin** | Mengelola pipeline, konfigurasi model statistik, threshold uji asumsi, dan monitoring job. |

---

## 4. User Requirements (UR)

| ID | Deskripsi |
|---|---|
| UR-1 | Pengguna dapat mengunggah file dataset dengan format standar (CSV/Excel). |
| UR-2 | Pengguna mendapatkan diagnosis struktur data otomatis: tipe data (numerik/kategori), jenis data (time-series/cross-sectional), jumlah grup, ukuran sampel (n), dan status berpasangan. |
| UR-3 | Sistem menentukan sumber data (kuesioner vs observasi/database sekunder) dan menjalankan uji validitas & reliabilitas instrumen jika sumbernya kuesioner. |
| UR-4 | Pengguna mendapatkan fallback otomatis: jika asumsi normalitas gagal, sistem mengalihkan ke uji non-parametrik tanpa intervensi manual. |
| UR-5 | Untuk data time-series, sistem otomatis menjalankan uji stasioneritas dan memilih model (differencing/transformasi bila tidak stasioner; ARIMA/VAR/Exponential Smoothing bila stasioner). |
| UR-6 | Pengguna **wajib memilih secara eksplisit** tujuan analisis (komparasi, pengaruh/regresi, korelasi, mediasi/moderasi) melalui parameter request; sistem tidak menebak tujuan ini secara otomatis, namun dapat memberi rekomendasi berdasarkan struktur data. Sistem lalu mengarahkan ke metode uji spesifik secara otomatis. |
| UR-7 | Pengguna menerima laporan analisis deskriptif (mean, median, SD, range) sebagai baseline sebelum hasil uji inferensial. |
| UR-8 | Pengguna menerima laporan interpretasi yang mudah dipahami (p-value, status signifikan, effect size, rekomendasi tindak lanjut), dalam Bahasa Indonesia secara default. |
| UR-9 | Pengguna dapat melacak riwayat analisis melalui Job ID yang menyimpan versi data dan parameter yang digunakan (reproducibility). |

---

## 5. Functional Requirements (FR)

### FR-01 — Ingestion & Metadata Detection Engine
- Mendeteksi tipe variabel (numerik/kategorik).
- Mendeteksi jenis data: Time-Series (TS) vs Cross-Sectional (CS).
- Mendeteksi jumlah grup, ukuran sampel (n), dan status berpasangan (paired/independen).
- Validasi skema dan format file (CSV/Excel).

### FR-02 — Preprocessing Pipeline
- Data cleaning (missing value handling, duplikasi).
- Deteksi & penanganan outlier.
- Transformasi data berbasis `sklearn.pipeline`.

### FR-03 — Source & Instrument Validation Module
- Jika sumber data = **Kuesioner**: jalankan Uji Validitas (korelasi item-total) dan Uji Reliabilitas (Cronbach's Alpha) sebelum lanjut ke uji asumsi.
- Jika sumber data = **Observasi/Database sekunder**: lewati uji instrumen, langsung ke pengecekan ukuran sampel (n).

### FR-04 — Sample Size Router
- Jika **n < 30** (default, dapat dikonfigurasi System Admin): prioritaskan uji non-parametrik dan Shapiro-Wilk sebagai uji normalitas utama.
- Jika **n ≥ 30**: jalankan uji kelayakan parametrik (Kolmogorov-Smirnov dengan Lilliefors correction).
- Jika n berada di bawah syarat minimum uji non-parametrik sekalipun (mis. n < 5 per grup), sistem mengembalikan error terstruktur alih-alih memaksakan uji yang tidak valid secara statistik.

### FR-05 — Time-Series Decision Engine
- Uji stasioneritas (mis. ADF Test).
- **Tidak stasioner** → Differencing/Transformasi, lalu uji ulang stasioneritas.
- **Stasioner** → pemilihan model: ARIMA / VAR / Exponential Smoothing.

### FR-06 — Assumption Testing Module (Gatekeeper)
- Uji normalitas (Shapiro-Wilk / Kolmogorov-Smirnov) sebagai gatekeeper utama parametrik vs non-parametrik di setiap cabang analisis (komparasi, korelasi).

### FR-06b — Descriptive Analysis Module
- Menghasilkan statistik ringkasan (mean, median, modus, standar deviasi, range) untuk seluruh jalur cross-sectional, dijalankan tepat setelah Sample Size Router (FR-04) dan sebelum Analysis Goal Router (FR-07 s.d. FR-10).
- Berlaku sebagai laporan baseline meski hasil uji inferensial lanjutan tidak signifikan.
- Tidak berlaku pada jalur Time-Series (FR-05), yang memiliki tahap deskriptif tersendiri (plot tren/musiman) di luar cakupan v1.

### FR-06c — Analysis Goal Selector
- Menerima parameter `analysis_goal` secara eksplisit dari pengguna (komparasi, pengaruh, korelasi, mediasi/moderasi) melalui request API.
- Sistem **tidak** menyimpulkan tujuan analisis secara otomatis dari struktur data, untuk menghindari kesimpulan yang menyimpang dari hipotesis penelitian pengguna.
- Sistem dapat menampilkan rekomendasi tujuan analisis berdasarkan struktur data (mis. dua variabel numerik kontinu → sarankan Korelasi/Pengaruh) sebagai *hint*, bukan keputusan otomatis.

### FR-07 — Comparative Analysis Engine (Tujuan: Komparasi)
Routing berdasarkan **jumlah grup**:
- **2 Grup, Independen**: Normal → Independent T-Test; Tidak normal → Mann-Whitney U.
- **2 Grup, Berpasangan**: Normal → Paired T-Test; Tidak normal → Wilcoxon Signed-Rank.
- **>2 Grup**: Normal → ANOVA; Tidak normal → Kruskal-Wallis.

### FR-08 — Associative/Influence Analysis Engine (Tujuan: Pengaruh)
- **>1 variabel independen**: Cek multikolinearitas/asumsi regresi berganda.
  - Aman → Regresi (Berganda).
  - Gagal → Transformasi/Drop variabel, lalu uji ulang.
- **Single variabel independen**: langsung Regresi Sederhana.

### FR-09 — Correlation Analysis Engine (Tujuan: Korelasi)
- Normal → Korelasi Pearson.
- Tidak normal → Korelasi Spearman/Kendall.

### FR-10 — Mediation/Moderation Analysis Engine (Tujuan: Mediasi/Moderasi)
- **Model Sederhana**: Path Analysis (Regresi Bertahap) + Sobel Test.
- **Model Kompleks/Multivariat**: Structural Equation Modeling (SEM).

### FR-11 — Evaluation & Interpretation Module
- Kalkulasi p-value dan effect size (Cohen's d, eta-squared, r, dsb. sesuai jenis uji).
- Generate interpretasi otomatis dalam bahasa natural (signifikan/tidak, kekuatan efek, rekomendasi).

### FR-12 — Job Tracking & Reproducibility Module
- Setiap analisis menghasilkan Job ID unik yang menyimpan snapshot data, parameter uji, dan hasil.

---

## 6. Non-Functional Requirements (NFR)

| Kategori | Ketentuan |
|---|---|
| **Performance** | Analisis dataset < 1.000 baris selesai dalam ≤ 3 detik. |
| **Scalability** | Arsitektur mendukung penambahan node komputasi (Worker) melalui Celery. |
| **Reliability** | Wajib ada error handling untuk data tidak memenuhi syarat uji (misal: data konstan, varians nol, n terlalu kecil untuk uji tertentu). |
| **Reproducibility** | Setiap hasil analisis dapat dilacak via Job ID yang menyimpan versi data & parameter. |
| **Security** | Data pengguna dienkripsi saat disimpan (at-rest) dan saat transit (TLS). |
| **Maintainability** | Decision engine harus modular (rule-based/config-driven) agar threshold uji asumsi dapat diubah tanpa deploy ulang kode. |

---

## 7. Success Metrics (KPI)

| Metrik | Target |
|---|---|
| **Accuracy** | Konsistensi output 100% terhadap standar kalkulasi statistik (dibandingkan R/SPSS). |
| **Automation Rate** | 90% dari total input pengguna dapat diselesaikan tanpa intervensi manual kritikal. |
| **Uptime** | Availability sistem backend ≥ 99.9%. |
| **Time-to-Insight** | Rata-rata waktu dari upload hingga laporan interpretasi < 5 detik untuk dataset standar. |

---

## 8. Data Flow Logic (Pipeline)

Alur mengikuti diagram keputusan sebagai berikut:

1. **Metadata Detection** — Tentukan tipe data, jenis (TS/CS), jumlah grup, n, dan status berpasangan.
2. **Cleaning & Outlier Check** — Pembersihan dasar dan deteksi outlier.
3. **Time Check** — Apakah data time-series?
   - **Ya** → Uji Stasioneritas → (Tidak Stasioner: Differencing/Transformasi; Stasioner: ARIMA/VAR/Exponential Smoothing) → Evaluasi.
   - **Tidak** → lanjut ke Source Check.
4. **Source Check** — Kuesioner (uji validitas & reliabilitas) atau Observasi/DB (langsung ke Sample Size Check).
5. **Sample Size Check (n)** — n < 30 → prioritaskan non-parametrik & Shapiro-Wilk; n ≥ 30 → uji kelayakan parametrik (Kolmogorov-Smirnov).
6. **Analisis Deskriptif** — Statistik ringkasan (mean/median/SD/range) sebagai baseline laporan, dijalankan sebelum tahap inferensial.
7. **Tujuan Analisis** (input eksplisit dari pengguna):
   - **Komparasi** → Jumlah grup → Berpasangan? → Uji Normalitas → pilih uji (T-Test/Mann-Whitney/Paired T-Test/Wilcoxon/ANOVA/Kruskal-Wallis).
   - **Pengaruh** → Jumlah variabel → Cek asumsi regresi → Regresi (sederhana/berganda).
   - **Korelasi** → Uji Normalitas → Pearson/Spearman.
   - **Mediasi/Moderasi** → Kompleksitas model → Path Analysis+Sobel Test / SEM.
8. **Evaluation** — Kalkulasi p-value & effect size, lalu output interpretasi otomatis.
9. **Selesai** — Laporan tersedia untuk diunduh/diakses via API.

---

## 9. Tech Stack Recommendations

| Layer | Teknologi |
|---|---|
| **Backend** | FastAPI (Python 3.12+) |
| **Frontend** | Next.js (dashboard visualisasi) |
| **Analytical Engine** | Scikit-learn Pipeline, Statsmodels (statistik inferensial & time-series), Pandas, Pingouin (effect size) |
| **Time-Series** | Statsmodels (ARIMA, VAR), `pmdarima` (auto-ARIMA), `statsmodels.tsa.stattools.adfuller` (uji stasioneritas) |
| **SEM/Path Analysis** | `semopy` atau integrasi R (`lavaan`) via `rpy2` jika diperlukan |
| **Task Queue** | Celery + Redis (proses analisis asinkron) |
| **Database** | PostgreSQL (metadata & job tracking) |

---

## 10. Out of Scope (v2.0)

- Analisis data kualitatif (teks/gambar/audio).
- Machine learning predictive modeling (klasifikasi/clustering) di luar konteks uji hipotesis.
- Visualisasi dashboard interaktif tingkat lanjut (akan menjadi PRD terpisah untuk modul Frontend).

---

## 11. Keputusan Desain yang Telah Diresolusi (v2.1)

Poin-poin berikut sebelumnya berstatus *open question* pada v2.0, kini ditetapkan sebagai default sistem (detail teknis lihat `Systemflow.md` §4.4):

| Poin | Keputusan |
|---|---|
| Sumber tujuan analisis (`analysis_goal`) | Input eksplisit dari pengguna, bukan deteksi otomatis. Sistem hanya boleh memberi rekomendasi. |
| Ambang n kecil vs n besar | **n = 30**, dapat dikonfigurasi System Admin. |
| Threshold VIF multikolinearitas | **VIF > 10** (opsi ketat VIF > 5 tersedia via konfigurasi). |
| Alpha signifikansi default | **0.05**, dapat dikonfigurasi per-request. |
| Bahasa output interpretasi | Bahasa Indonesia (default), opsi Bahasa Inggris. |
| Penanganan n terlampau kecil | Minimum sample size guard — mengembalikan error terstruktur, bukan memaksakan uji. |

## 12. Open Questions (Tersisa)

1. Apakah sistem perlu mendukung *multiple comparison correction* (Bonferroni, Tukey HSD) untuk ANOVA post-hoc? Ya wajib
2. Apakah SEM akan menjadi fitur v1 atau dijadwalkan sebagai fase 2 mengingat kompleksitas implementasi (dependensi `semopy`/`lavaan` via `rpy2`)? tidak, akan dilakukan pada fase 2
3. Apakah perlu dukungan uji KPSS (selain ADF) untuk konfirmasi silang stasioneritas pada jalur time-series, sebagaimana disarankan pada `Systemflow.md`? ya
