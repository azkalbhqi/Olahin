import os
import uuid
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
from fastapi import UploadFile, HTTPException
from app.config import UPLOAD_DIR

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

def get_file_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    return ext

def validate_file_extension(filename: str) -> str:
    ext = get_file_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format file tidak didukung. Hanya mengizinkan: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return ext

def infer_column_type(series: pd.Series) -> str:
    """
    Helper to detect if a pandas series is numeric or categorical.
    """
    if pd.api.types.is_numeric_dtype(series):
        # Even if numeric, if it has very low cardinality (e.g. binary 0/1), it might be categorical,
        # but standard routing is based on dtype.
        return "numerical"
    return "categorical"

def detect_data_structure(df: pd.DataFrame) -> Tuple[str, Optional[str]]:
    """
    Detects if the dataframe is a time series or cross-sectional.
    Looks for datetime columns or date-like column names.
    """
    time_keywords = ['date', 'time', 'year', 'month', 'day', 'tanggal', 'tahun', 'bulan', 'hari', 'timestamp']
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in time_keywords):
            try:
                # Avoid converting completely unrelated strings by checking if conversion succeeds
                parsed = pd.to_datetime(df[col], errors='coerce')
                if parsed.notna().sum() > 0.8 * len(df):
                    return "time_series", str(col)
            except Exception:
                pass
                
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return "time_series", str(col)
            
    return "cross_sectional", None

def save_and_ingest_file(file: UploadFile) -> Dict[str, Any]:
    """
    Saves the uploaded file, reads it into a Pandas DataFrame,
    and extracts metadata.
    """
    original_filename = file.filename
    if not original_filename:
        raise HTTPException(status_code=400, detail="Nama file tidak valid.")
        
    ext = validate_file_extension(original_filename)
    
    # Generate unique ID and save path
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)
    
    try:
        # Save file to disk chunk by chunk
        with open(file_path, "wb") as f:
            while content := file.file.read(1024 * 1024): # 1MB chunks
                f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menyimpan file: {str(e)}"
        )
    
    # Read the file to extract metadata
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".xlsx":
            df = pd.read_excel(file_path, engine="openpyxl")
        elif ext == ".xls":
            df = pd.read_excel(file_path, engine="xlrd")
        else:
            raise HTTPException(status_code=400, detail="Format file tidak didukung.")
    except Exception as e:
        # Clean up file on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file data. Pastikan file tidak rusak. Detail: {str(e)}"
        )
        
    row_count = len(df)
    col_count = len(df.columns)
    columns = df.columns.tolist()
    
    # Check minimum row count
    if row_count < 5:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Data terlalu sedikit (hanya {row_count} baris). Minimum data yang diperlukan adalah 5 baris."
        )
        
    # Infer basic data types for columns
    column_types = {col: infer_column_type(df[col]) for col in columns}
    
    # Detect structure
    data_struct, time_col = detect_data_structure(df)
    
    return {
        "file_id": file_id,
        "filename": original_filename,
        "row_count": row_count,
        "col_count": col_count,
        "columns": columns,
        "column_types": column_types,
        "data_structure": data_struct
    }

def load_dataframe(file_id: str) -> Tuple[pd.DataFrame, str]:
    """
    Helper to locate and load a dataframe from disk by its file_id.
    Returns the dataframe and its file extension.
    """
    # Search for the file in the upload directory
    found_file = None
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            found_file = filename
            break
            
    if not found_file:
        raise HTTPException(
            status_code=404,
            detail=f"Data dengan ID {file_id} tidak ditemukan. Silakan unggah kembali."
        )
        
    file_path = os.path.join(UPLOAD_DIR, found_file)
    ext = get_file_extension(found_file)
    
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".xlsx":
            df = pd.read_excel(file_path, engine="openpyxl")
        elif ext == ".xls":
            df = pd.read_excel(file_path, engine="xlrd")
        else:
            raise HTTPException(status_code=400, detail="Format file tidak didukung.")
        return df, ext
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memuat file: {str(e)}"
        )
