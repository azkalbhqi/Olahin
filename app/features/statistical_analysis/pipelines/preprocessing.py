import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from fastapi import HTTPException

def run_preprocessing(
    df: pd.DataFrame, 
    selected_columns: List[str]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes automated preprocessing on the DataFrame for the selected columns.
    
    Steps:
    1. Data Type Inference & Conversion
    2. Missing Value Handling (Drop if < 5%, Impute if >= 5%)
    3. Outlier Filtering using IQR for numerical columns
    
    Returns the cleaned DataFrame and a dictionary containing logs of the operations.
    """
    cleaned_df = df.copy()
    logs = {
        "initial_rows": len(cleaned_df),
        "data_types": {},
        "missing_values": {},
        "outliers_removed": {},
        "final_rows": 0,
        "actions_taken": []
    }
    
    if len(cleaned_df) == 0:
        raise HTTPException(status_code=400, detail="Dataset kosong.")
        
    # --- 1. Data Type Inference & Conversion ---
    for col in selected_columns:
        if col not in cleaned_df.columns:
            raise HTTPException(status_code=400, detail=f"Kolom '{col}' tidak ditemukan dalam dataset.")
            
        # Try to convert to numeric if appropriate
        col_series = cleaned_df[col]
        
        # If it's object type but contains numeric-like data, convert it
        if col_series.dtype == 'object':
            # Check if we can convert it without losing too much data
            converted = pd.to_numeric(col_series, errors='coerce')
            # If less than 20% of values become NaN, we treat it as numeric
            if converted.isna().sum() - col_series.isna().sum() < 0.2 * len(col_series):
                cleaned_df[col] = converted
                logs["actions_taken"].append(f"Kolom '{col}' dikonversi ke tipe numerik.")
                
        # Final inference check
        if pd.api.types.is_numeric_dtype(cleaned_df[col]):
            logs["data_types"][col] = "numerical"
        else:
            # Cast categorical columns to string for consistency
            cleaned_df[col] = cleaned_df[col].astype(str)
            # Replace 'nan' string (resulting from cast of NaN) back to actual NaN
            cleaned_df[col] = cleaned_df[col].replace('nan', np.nan)
            logs["data_types"][col] = "categorical"

    # --- 2. Handling Missing Values ---
    # First, separate columns by missing value percentages
    to_drop_cols = []
    to_impute_cols = []
    
    total_rows = len(cleaned_df)
    
    for col in selected_columns:
        missing_count = cleaned_df[col].isna().sum()
        if missing_count == 0:
            logs["missing_values"][col] = {"count": 0, "percentage": 0.0, "strategy": "none"}
            continue
            
        pct = (missing_count / total_rows) * 100
        logs["missing_values"][col] = {"count": int(missing_count), "percentage": round(pct, 2)}
        
        if pct < 5.0:
            to_drop_cols.append(col)
            logs["missing_values"][col]["strategy"] = "drop"
        else:
            to_impute_cols.append(col)
            logs["missing_values"][col]["strategy"] = "impute"

    # Execute Drops
    if to_drop_cols:
        before_drop = len(cleaned_df)
        cleaned_df = cleaned_df.dropna(subset=to_drop_cols)
        dropped_count = before_drop - len(cleaned_df)
        if dropped_count > 0:
            logs["actions_taken"].append(
                f"Menghapus {dropped_count} baris yang memiliki nilai kosong pada kolom: {', '.join(to_drop_cols)} (karena data kosong < 5%)."
            )

    # Execute Imputations
    for col in to_impute_cols:
        col_type = logs["data_types"][col]
        missing_count = cleaned_df[col].isna().sum()
        if missing_count == 0:
            continue
            
        if col_type == "numerical":
            median_val = cleaned_df[col].median()
            # If median is NaN (all values are NaN), use 0
            if pd.isna(median_val):
                median_val = 0.0
            cleaned_df[col] = cleaned_df[col].fillna(median_val)
            logs["actions_taken"].append(
                f"Mengimputasi {missing_count} nilai kosong pada kolom '{col}' dengan nilai Median ({median_val:.2f}) (karena data kosong >= 5%)."
            )
            logs["missing_values"][col]["imputed_value"] = float(median_val)
        else:
            # Categorical imputation using mode
            mode_series = cleaned_df[col].mode()
            mode_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
            cleaned_df[col] = cleaned_df[col].fillna(mode_val)
            logs["actions_taken"].append(
                f"Mengimputasi {missing_count} nilai kosong pada kolom '{col}' dengan nilai Modus ('{mode_val}') (karena data kosong >= 5%)."
            )
            logs["missing_values"][col]["imputed_value"] = str(mode_val)

    # --- 3. Outlier Filtering (IQR) ---
    # We only apply IQR to numerical columns
    for col in selected_columns:
        if logs["data_types"][col] == "numerical":
            col_series = cleaned_df[col]
            q1 = col_series.quantile(0.25)
            q3 = col_series.quantile(0.75)
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # Find outliers
            outliers = cleaned_df[(cleaned_df[col] < lower_bound) | (cleaned_df[col] > upper_bound)]
            outlier_count = len(outliers)
            
            if outlier_count > 0:
                # Filter out outliers
                cleaned_df = cleaned_df[(cleaned_df[col] >= lower_bound) & (cleaned_df[col] <= upper_bound)]
                logs["outliers_removed"][col] = {
                    "count": outlier_count,
                    "lower_bound": round(lower_bound, 4),
                    "upper_bound": round(upper_bound, 4)
                }
                logs["actions_taken"].append(
                    f"Mendeteksi dan menghapus {outlier_count} baris outlier pada kolom '{col}' dengan rentang IQR [{lower_bound:.2f}, {upper_bound:.2f}]."
                )
            else:
                logs["outliers_removed"][col] = {"count": 0}

    logs["final_rows"] = len(cleaned_df)
    
    if len(cleaned_df) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Data setelah pembersihan terlalu sedikit (hanya {len(cleaned_df)} baris). "
                   "Gagal melanjutkan analisis statistik. Silakan periksa kembali dataset Anda."
        )
        
    return cleaned_df, logs
