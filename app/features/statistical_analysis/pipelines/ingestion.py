import os
import uuid
from typing import Dict, List, Tuple, Any
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
    
    # Infer basic data types for columns
    column_types = {col: infer_column_type(df[col]) for col in columns}
    
    return {
        "file_id": file_id,
        "filename": original_filename,
        "row_count": row_count,
        "col_count": col_count,
        "columns": columns,
        "column_types": column_types
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
