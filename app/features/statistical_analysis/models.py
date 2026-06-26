from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UploadResponse(BaseModel):
    file_id: str = Field(..., description="ID unik file yang diunggah untuk referensi analisis")
    filename: str = Field(..., description="Nama file asli")
    row_count: int = Field(..., description="Jumlah baris data")
    col_count: int = Field(..., description="Jumlah kolom data")
    columns: List[str] = Field(..., description="Daftar nama kolom")
    column_types: Dict[str, str] = Field(..., description="Tipe data tiap kolom hasil deteksi otomatis")

class AnalysisRequest(BaseModel):
    file_id: str = Field(..., description="ID file hasil unggahan")
    independent_vars: List[str] = Field(default=[], description="Daftar kolom variabel independen (X) - dibutuhkan untuk Asosiatif")
    dependent_var: str = Field(..., description="Kolom variabel dependen (Y)")
    analysis_type: str = Field("Asosiatif", description="Tipe analisis: 'Asosiatif' (hubungan/regresi) atau 'Komparatif' (perbandingan)")
    group_var: Optional[str] = Field(None, description="Kolom variabel grup (Kategorikal) - dibutuhkan untuk Komparatif")

class AnalysisResponse(BaseModel):
    file_id: str = Field(..., description="ID file yang dianalisis")
    preprocessing_log: Dict[str, Any] = Field(..., description="Log hasil tindakan pembersihan data (imputasi, drop, outlier)")
    normality_test: Dict[str, Any] = Field(..., description="Hasil pengujian normalitas otomatis")
    routing: Dict[str, Any] = Field(..., description="Hasil keputusan routing statistika (uji yang dipilih)")
    statistics: Dict[str, Any] = Field(..., description="Hasil perhitungan numerik uji statistik")
    narrative: str = Field(..., description="Terjemahan naratif dalam Bahasa Indonesia")
    plot_base64: str = Field(..., description="Grafik visualisasi yang di-encode ke Base64")
    report_url: str = Field(..., description="URL unduhan laporan dokumen Word (.docx)")
