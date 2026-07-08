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

router = APIRouter(
    prefix="/api/statistical-analysis",
    tags=["Statistical Analysis"]
)

def get_base_url(request: Request) -> str:
    """
    Dapatkan base URL untuk menghasilkan tautan unduhan absolut.
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
    dan pembuatan laporan .docx & .pdf lengkap dengan grafik.
    """
    # 1. Load DataFrame (Pipeline 1 helper)
    df, ext = load_dataframe(request.file_id)
    
    # Backwards compatibility & Mapping analysis_goal
    goal = request.analysis_goal
    if request.analysis_type and not request.analysis_goal:
        if request.analysis_type == "Asosiatif":
            goal = "pengaruh"
        elif request.analysis_type == "Komparatif":
            goal = "komparasi"
            
    # Check early if it is a Time-Series Path (FR-05)
    is_ts = False
    time_column = request.time_col
    
    from app.features.statistical_analysis.pipelines.ingestion import detect_data_structure
    data_struct, detected_time_col = detect_data_structure(df)
    
    if time_column:
        is_ts = True
    elif data_struct == "time_series":
        # Only route to time_series automatically if not doing other specific comparative/mediation goals
        if goal not in ["komparasi", "korelasi", "mediasi_moderasi"]:
            is_ts = True
            time_column = detected_time_col
            
    # Validate request fields based on path
    if not request.dependent_var:
        raise HTTPException(status_code=400, detail="Variabel dependen wajib diisi.")
        
    target_columns = [request.dependent_var]
    
    if is_ts:
        # Time-Series: independent variables are optional (univariate ARIMA vs multivariate VAR)
        if request.independent_vars:
            for var in request.independent_vars:
                if var not in target_columns:
                    target_columns.append(var)
        if time_column and time_column not in target_columns:
            target_columns.append(time_column)
    else:
        # Cross-Sectional validation rules
        if goal == "komparasi":
            if not request.group_var:
                raise HTTPException(status_code=400, detail="Variabel grup (group_var) wajib diisi untuk analisis komparatif.")
            target_columns.append(request.group_var)
        elif goal == "pengaruh" or goal == "korelasi":
            if not request.independent_vars:
                raise HTTPException(status_code=400, detail="Variabel independen harus dipilih minimal satu.")
            for var in request.independent_vars:
                if var not in target_columns:
                    target_columns.append(var)
        elif goal == "mediasi_moderasi":
            if not request.independent_vars:
                raise HTTPException(status_code=400, detail="Variabel independen (X) harus dipilih.")
            for var in request.independent_vars:
                if var not in target_columns:
                    target_columns.append(var)
            if not request.mediator_var:
                raise HTTPException(status_code=400, detail="Variabel mediator (mediator_var) harus ditentukan.")
            if request.mediator_var not in target_columns:
                target_columns.append(request.mediator_var)
                
    # 2. Run Preprocessing Engine (Pipeline 2)
    cleaned_df, prep_log = run_preprocessing(df, target_columns)
    
    descriptive_stats = {}
    instrument_res = None
    ts_results = None
    normality_res = {}
    routing_info = {}
    analysis_res = {}
    
    if is_ts:
        # --- Time-Series Path ---
        from app.features.statistical_analysis.pipelines.statistics import run_time_series_path
        ts_results = run_time_series_path(
            df=cleaned_df,
            dependent_var=request.dependent_var,
            independent_vars=request.independent_vars,
            time_col=time_column
        )
        
        routing_info = {
            "chosen_test": ts_results["model_type"],
            "is_parametric": True
        }
        
        # Format dummy standard metrics for compatibility in client response
        analysis_res = ts_results["model_details"]
        analysis_res["model_type"] = ts_results["model_type"]
        analysis_res["is_parametric"] = True
        
        normality_res = {
            "test_name": "KPSS & ADF (Stasioneritas)",
            "sample_size": len(cleaned_df),
            "statistic": 0.0,
            "p_value": 1.0,
            "is_normal": True
        }
    else:
        # --- Cross-Sectional Path ---
        # A. Instrument Validation for questionnaires
        if request.data_source == "questionnaire":
            from app.features.statistical_analysis.pipelines.statistics import run_instrument_validation
            instrument_res = run_instrument_validation(cleaned_df, request.independent_vars)
            
        # B. Run Descriptive Stats
        from app.features.statistical_analysis.pipelines.statistics import run_descriptive_analysis
        desc_cols = [request.dependent_var]
        for var in request.independent_vars:
            if var not in desc_cols:
                desc_cols.append(var)
        if request.mediator_var and request.mediator_var not in desc_cols:
            desc_cols.append(request.mediator_var)
            
        descriptive_stats = run_descriptive_analysis(cleaned_df, desc_cols)
        
        # C. Run Routing & Hypothesis Analysis
        from app.features.statistical_analysis.pipelines.statistics import execute_routing_and_analysis
        normality_res, analysis_res = execute_routing_and_analysis(
            df=cleaned_df,
            analysis_goal=goal,
            independent_vars=request.independent_vars,
            dependent_var=request.dependent_var,
            group_var=request.group_var,
            is_paired=request.is_paired,
            mediator_var=request.mediator_var,
            alpha=request.alpha
        )
        
        routing_info = {
            "chosen_test": analysis_res["model_type"],
            "is_parametric": analysis_res["is_parametric"]
        }
        
    # 4. Generate Narrative Interpretation (Pipeline 4)
    from app.features.statistical_analysis.pipelines.interpretation import generate_narrative_interpretation
    narrative = generate_narrative_interpretation(
        normality_results=normality_res,
        analysis_results=analysis_res,
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        group_var=request.group_var,
        descriptive_stats=descriptive_stats,
        instrument_validation=instrument_res,
        time_series_results=ts_results,
        alpha=request.alpha
    )
    
    # 5. Visualization & Export Reports (Pipeline 5)
    from app.features.statistical_analysis.pipelines.visualization import (
        generate_plot,
        encode_image_base64,
        create_docx_report,
        create_pdf_report
    )
    
    plot_buf = generate_plot(
        df=cleaned_df,
        model_type=routing_info["chosen_test"],
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        group_var=request.group_var,
        time_col=time_column,
        time_series_results=ts_results,
        analysis_results=analysis_res
    )
    
    plot_b64 = encode_image_base64(plot_buf)
    
    # Word docx report
    report_filename = create_docx_report(
        file_id=request.file_id,
        research_title=request.research_title,
        filename=f"Data_{request.file_id}{ext}",
        preprocessing_log=prep_log,
        normality_results=normality_res,
        analysis_results=analysis_res,
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        narrative=narrative,
        plot_buf=plot_buf,
        group_var=request.group_var,
        descriptive_stats=descriptive_stats,
        instrument_validation=instrument_res,
        time_series_results=ts_results
    )
    
    # PDF report
    pdf_filename = create_pdf_report(
        file_id=request.file_id,
        research_title=request.research_title,
        filename=f"Data_{request.file_id}{ext}",
        preprocessing_log=prep_log,
        normality_results=normality_res,
        analysis_results=analysis_res,
        independent_vars=request.independent_vars,
        dependent_var=request.dependent_var,
        narrative=narrative,
        plot_buf=plot_buf,
        group_var=request.group_var,
        descriptive_stats=descriptive_stats,
        instrument_validation=instrument_res,
        time_series_results=ts_results
    )
    
    base_url = get_base_url(req)
    report_url = f"{base_url}api/statistical-analysis/download/{report_filename}"
    report_pdf_url = f"{base_url}api/statistical-analysis/download/{pdf_filename}"
    
    return AnalysisResponse(
        file_id=request.file_id,
        preprocessing_log=prep_log,
        normality_test=normality_res,
        routing=routing_info,
        statistics=analysis_res,
        descriptive_stats=descriptive_stats,
        instrument_validation=instrument_res,
        time_series_results=ts_results,
        narrative=narrative,
        plot_base64=plot_b64,
        report_url=report_url,
        report_pdf_url=report_pdf_url
    )

@router.get("/download/{filename}", summary="Unduh File Laporan (Word atau PDF)")
async def download_report(filename: str):
    """
    Mengunduh file laporan dalam format Word (.docx) atau PDF (.pdf) berdasarkan nama file.
    """
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(EXPORT_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail="File laporan tidak ditemukan atau sudah kedaluwarsa."
        )
        
    _, ext = os.path.splitext(safe_filename.lower())
    if ext == ".pdf":
        media_type = "application/pdf"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_filename
    )

@router.get("/download/raw/{filename}", summary="Unduh File Data Mentah (CSV/Excel)")
async def download_raw_file(filename: str):
    """
    Mengunduh file data mentah (.csv, .xlsx, .xls) yang telah diunggah sebelumnya.
    """
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail="File data mentah tidak ditemukan."
        )
        
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
