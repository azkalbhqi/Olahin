import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from app.config import EXPORT_DIR, UPLOAD_DIR
from app.features.statistical_analysis.models import (
    UploadResponse,
    AnalysisRequest,
    AnalysisResponse
)
from app.features.statistical_analysis.pipelines.ingestion import (
    save_and_ingest_file,
    load_dataframe
)
from app.features.statistical_analysis.pipelines.preprocessing import run_preprocessing
from app.features.statistical_analysis.pipelines.statistics import execute_routing_and_analysis
from app.features.statistical_analysis.pipelines.interpretation import generate_narrative_interpretation
from app.features.statistical_analysis.pipelines.visualization import (
    generate_plot,
    encode_image_base64,
    create_docx_report
)

router = APIRouter(
    prefix="/api/statistical-analysis",
    tags=["Statistical Analysis"]
)

def get_base_url(request: Request) -> str:
    """
    Dapatkan base URL untuk menghasilkan tautan unduhan absolut.
    Pertama memeriksa konfigurasi BACKEND_URL, lalu header X-Forwarded (untuk proxy),
    dan jika tidak ada, fallback ke request.base_url bawaan.
    """
    from app.config import BACKEND_URL
    if BACKEND_URL:
        url = BACKEND_URL if BACKEND_URL.endswith("/") else f"{BACKEND_URL}/"
        return url
        
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    if forwarded_host:
        proto = forwarded_proto or "http"
        return f"{proto}://{forwarded_host}/"
        
    return str(request.base_url)

@router.post("/upload", response_model=UploadResponse, summary="Ingest dan Validasi File Data")
async def upload_file(file: UploadFile = File(..., description="File data (.csv, .xlsx, .xls)")):
    """
    Mengunggah file dataset, memvalidasi format ekstensi,
    dan mengekstrak deskripsi kolom serta jumlah baris awal.
    """
    return save_and_ingest_file(file)

@router.post("/analyze", response_model=AnalysisResponse, summary="Jalankan Pipeline Analisis Statistik Otomatis")
async def analyze_data(request: AnalysisRequest, req: Request):
    """
    Menjalankan pipeline preprocessing, analisis statistik, interpretasi naratif,
    dan pembuatan laporan .docx lengkap dengan grafik.
    """
    # 1. Load DataFrame (Pipeline 1 helper)
    df, ext = load_dataframe(request.file_id)
    
    # Identify variables of interest
    target_columns = []
    
    # Append dependent variable
    if not request.dependent_var:
        raise HTTPException(status_code=400, detail="Variabel dependen wajib diisi.")
    target_columns.append(request.dependent_var)
    
    # Append independent variables (for associative)
    if request.analysis_type == "Asosiatif":
        if not request.independent_vars:
            raise HTTPException(status_code=400, detail="Variabel independen harus dipilih minimal satu.")
        for var in request.independent_vars:
            if var not in target_columns:
                target_columns.append(var)
                
    # Append grouping variable (for comparative)
    elif request.analysis_type == "Komparatif":
        if not request.group_var:
            raise HTTPException(status_code=400, detail="Variabel grup (group_var) wajib diisi untuk analisis komparatif.")
        if request.group_var not in target_columns:
            target_columns.append(request.group_var)
            
    # 2. Run Preprocessing Engine (Pipeline 2)
    cleaned_df, prep_log = run_preprocessing(df, target_columns)
    
    # 3. Statistical Routing and Execution (Pipeline 3)
    normality_res, analysis_res = execute_routing_and_analysis(
        df=cleaned_df,
        analysis_type=request.analysis_type,
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        group_var=request.group_var
    )
    
    # 4. Generate Narrative Interpretation (Pipeline 4)
    narrative = generate_narrative_interpretation(
        normality_results=normality_res,
        analysis_results=analysis_res,
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        group_var=request.group_var
    )
    
    # 5. Visualization & Export Report (Pipeline 5)
    model_type = analysis_res["model_type"]
    plot_buf = generate_plot(
        df=cleaned_df,
        model_type=model_type,
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        group_var=request.group_var
    )
    
    plot_b64 = encode_image_base64(plot_buf)
    
    # Find original file name
    # We can reconstruct it or read it. Let's pass a generic name or check upload log
    # For now, let's name it based on the analysis type
    report_filename = create_docx_report(
        file_id=request.file_id,
        filename=f"Data_{request.file_id}{ext}",
        preprocessing_log=prep_log,
        normality_results=normality_res,
        analysis_results=analysis_res,
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        narrative=narrative,
        plot_buf=plot_buf,
        group_var=request.group_var
    )
    
    # Determine local/server base URL to build the download link (supporting reverse proxies & env BACKEND_URL)
    base_url = get_base_url(req)
    report_url = f"{base_url}api/statistical-analysis/download/{report_filename}"
    
    routing_info = {
        "chosen_test": model_type,
        "is_parametric": analysis_res["is_parametric"]
    }
    
    return AnalysisResponse(
        file_id=request.file_id,
        preprocessing_log=prep_log,
        normality_test=normality_res,
        routing=routing_info,
        statistics=analysis_res,
        narrative=narrative,
        plot_base64=plot_b64,
        report_url=report_url
    )

@router.get("/download/{filename}", summary="Unduh File Laporan Word")
async def download_report(filename: str):
    """
    Mengunduh file laporan dalam format Word (.docx) berdasarkan nama file.
    """
    # Mencegah serangan path traversal dengan membersihkan nama file
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(EXPORT_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail="File laporan tidak ditemukan atau sudah kedaluwarsa."
        )
        
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_filename
    )

@router.get("/download/raw/{filename}", summary="Unduh File Data Mentah (CSV/Excel)")
async def download_raw_file(filename: str):
    """
    Mengunduh file data mentah (.csv, .xlsx, .xls) yang telah diunggah sebelumnya.
    """
    # Mencegah serangan path traversal dengan membersihkan nama file
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail="File data mentah tidak ditemukan."
        )
        
    # Tentukan media_type berdasarkan ekstensi file
    _, ext = os.path.splitext(safe_filename.lower())
    if ext == ".csv":
        media_type = "text/csv"
    elif ext in (".xlsx", ".xls"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "application/octet-stream"
        
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_filename
    )
