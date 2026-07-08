from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UploadResponse(BaseModel):
    file_id: str = Field(..., description="ID unik file yang diunggah untuk referensi analisis")
    filename: str = Field(..., description="Nama file asli")
    row_count: int = Field(..., description="Jumlah baris data")
    col_count: int = Field(..., description="Jumlah kolom data")
    columns: List[str] = Field(..., description="Daftar nama kolom")
    column_types: Dict[str, str] = Field(..., description="Tipe data tiap kolom hasil deteksi otomatis")
    data_structure: str = Field("cross_sectional", description="Struktur data: 'cross_sectional' atau 'time_series'")

class AnalysisRequest(BaseModel):
    file_id: str = Field(..., description="ID file hasil unggahan")
    independent_vars: List[str] = Field(default=[], description="Daftar kolom variabel independen (X)")
    dependent_var: str = Field(..., description="Kolom variabel dependen (Y)")
    analysis_goal: str = Field("pengaruh", description="Tujuan analisis: 'komparasi', 'pengaruh', 'korelasi', atau 'mediasi_moderasi'")
    analysis_type: Optional[str] = Field(None, description="Legacy field untuk kecocokan tipe analisis")
    group_var: Optional[str] = Field(None, description="Kolom variabel grup (Kategorikal) - dibutuhkan untuk Komparatif")
    research_title: str = Field("Analisis_Statistik", description="Judul penelitian untuk penamaan file laporan")
    is_paired: bool = Field(False, description="Apakah data berpasangan (paired) - untuk komparasi")
    data_source: str = Field("observation", description="Sumber data: 'observation' atau 'questionnaire'")
    mediator_var: Optional[str] = Field(None, description="Variabel mediator - untuk mediasi")
    alpha: float = Field(0.05, description="Signifikansi level (alpha)")
    time_col: Optional[str] = Field(None, description="Kolom waktu - untuk time-series")

class AnalysisResponse(BaseModel):
    file_id: str = Field(..., description="ID file yang dianalisis")
    preprocessing_log: Dict[str, Any] = Field(..., description="Log hasil tindakan pembersihan data (imputasi, drop, outlier)")
    normality_test: Dict[str, Any] = Field(..., description="Hasil pengujian normalitas otomatis")
    routing: Dict[str, Any] = Field(..., description="Hasil keputusan routing statistika (uji yang dipilih)")
    statistics: Dict[str, Any] = Field(..., description="Hasil perhitungan numerik uji statistik")
    descriptive_stats: Dict[str, Any] = Field(default={}, description="Statistik deskriptif variabel")
    instrument_validation: Optional[Dict[str, Any]] = Field(None, description="Hasil uji validitas dan reliabilitas instrumen")
    time_series_results: Optional[Dict[str, Any]] = Field(None, description="Hasil uji stasioneritas dan model time-series")
    narrative: str = Field(..., description="Terjemahan naratif dalam Bahasa Indonesia")
    plot_base64: str = Field(..., description="Grafik visualisasi yang di-encode ke Base64")
    report_url: str = Field(..., description="URL unduhan laporan dokumen Word (.docx)")
    report_pdf_url: str = Field(..., description="URL unduhan laporan dokumen PDF (.pdf)")
