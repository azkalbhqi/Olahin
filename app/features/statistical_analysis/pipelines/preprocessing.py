import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from fastapi import HTTPException
from sklearn.base import BaseEstimator, TransformerMixin

class TypeConverter(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer for type inference and conversion.
    """
    def __init__(self, selected_columns: List[str]):
        self.selected_columns = selected_columns
        self.actions_taken = []
        self.data_types = {}
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X, y=None):
        X = X.copy()
        for col in self.selected_columns:
            if col not in X.columns:
                raise HTTPException(status_code=400, detail=f"Kolom '{col}' tidak ditemukan dalam dataset.")
                
            series = X[col]
            
            # Object to numeric if <= 20% NaN conversion loss
            if series.dtype == 'object':
                converted = pd.to_numeric(series, errors='coerce')
                # If less than 20% of values become NaN, we treat it as numeric
                if (converted.isna().sum() - series.isna().sum()) < 0.2 * len(series):
                    X[col] = converted
                    self.actions_taken.append(f"Kolom '{col}' dikonversi ke tipe numerik.")
                    
            if pd.api.types.is_numeric_dtype(X[col]):
                self.data_types[col] = "numerical"
            else:
                X[col] = X[col].astype(str)
                # Replace 'nan' string back to actual NaN
                X[col] = X[col].replace('nan', np.nan)
                self.data_types[col] = "categorical"
        return X

class MissingValueHandler(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer for missing value drop and imputation.
    """
    def __init__(self, selected_columns: List[str], data_types: Dict[str, str]):
        self.selected_columns = selected_columns
        self.data_types = data_types
        self.missing_values = {}
        self.actions_taken = []
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X, y=None):
        X = X.copy()
        to_drop_cols = []
        to_impute_cols = []
        total_rows = len(X)
        
        if total_rows == 0:
            return X
            
        for col in self.selected_columns:
            missing_count = X[col].isna().sum()
            if missing_count == 0:
                self.missing_values[col] = {"count": 0, "percentage": 0.0, "strategy": "none"}
                continue
                
            pct = (missing_count / total_rows) * 100
            self.missing_values[col] = {"count": int(missing_count), "percentage": round(pct, 2)}
            
            if pct < 5.0:
                to_drop_cols.append(col)
                self.missing_values[col]["strategy"] = "drop"
            else:
                to_impute_cols.append(col)
                self.missing_values[col]["strategy"] = "impute"
                
        # Drop columns with low missingness (< 5%)
        if to_drop_cols:
            before_drop = len(X)
            X = X.dropna(subset=to_drop_cols)
            dropped_count = before_drop - len(X)
            if dropped_count > 0:
                self.actions_taken.append(
                    f"Menghapus {dropped_count} baris yang memiliki nilai kosong pada kolom: {', '.join(to_drop_cols)} (karena data kosong < 5%)."
                )
                
        # Imputations for columns with high missingness (>= 5%)
        for col in to_impute_cols:
            col_type = self.data_types.get(col, "numerical")
            missing_count = X[col].isna().sum()
            if missing_count == 0:
                continue
                
            if col_type == "numerical":
                median_val = X[col].median()
                if pd.isna(median_val):
                    median_val = 0.0
                X[col] = X[col].fillna(median_val)
                self.actions_taken.append(
                    f"Mengimputasi {missing_count} nilai kosong pada kolom '{col}' dengan nilai Median ({median_val:.2f}) (karena data kosong >= 5%)."
                )
                self.missing_values[col]["imputed_value"] = float(median_val)
            else:
                mode_series = X[col].mode()
                mode_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                X[col] = X[col].fillna(mode_val)
                self.actions_taken.append(
                    f"Mengimputasi {missing_count} nilai kosong pada kolom '{col}' dengan nilai Modus ('{mode_val}') (karena data kosong >= 5%)."
                )
                self.missing_values[col]["imputed_value"] = str(mode_val)
                
        return X

class OutlierFilter(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer for outlier filtering using IQR.
    """
    def __init__(self, selected_columns: List[str], data_types: Dict[str, str]):
        self.selected_columns = selected_columns
        self.data_types = data_types
        self.outliers_removed = {}
        self.actions_taken = []
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X, y=None):
        X = X.copy()
        for col in self.selected_columns:
            if self.data_types.get(col) == "numerical":
                col_series = X[col]
                if len(col_series) < 4:
                    self.outliers_removed[col] = {"count": 0}
                    continue
                    
                q1 = col_series.quantile(0.25)
                q3 = col_series.quantile(0.75)
                iqr = q3 - q1
                
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                outliers = X[(X[col] < lower_bound) | (X[col] > upper_bound)]
                outlier_count = len(outliers)
                
                if outlier_count > 0:
                    X = X[(X[col] >= lower_bound) & (X[col] <= upper_bound)]
                    self.outliers_removed[col] = {
                        "count": outlier_count,
                        "lower_bound": round(lower_bound, 4),
                        "upper_bound": round(upper_bound, 4)
                    }
                    self.actions_taken.append(
                        f"Mendeteksi dan menghapus {outlier_count} baris outlier pada kolom '{col}' dengan rentang IQR [{lower_bound:.2f}, {upper_bound:.2f}]."
                    )
                else:
                    self.outliers_removed[col] = {"count": 0}
        return X

def run_preprocessing(
    df: pd.DataFrame, 
    selected_columns: List[str]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes automated preprocessing on the DataFrame using the scikit-learn components.
    """
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="Dataset kosong.")
        
    # Run sequentially
    converter = TypeConverter(selected_columns)
    df_converted = converter.fit_transform(df)
    
    imputer = MissingValueHandler(selected_columns, converter.data_types)
    df_imputed = imputer.fit_transform(df_converted)
    
    outlier_remover = OutlierFilter(selected_columns, converter.data_types)
    df_cleaned = outlier_remover.fit_transform(df_imputed)
    
    actions = converter.actions_taken + imputer.actions_taken + outlier_remover.actions_taken
    
    logs = {
        "initial_rows": len(df),
        "data_types": converter.data_types,
        "missing_values": imputer.missing_values,
        "outliers_removed": outlier_remover.outliers_removed,
        "final_rows": len(df_cleaned),
        "actions_taken": actions
    }
    
    if len(df_cleaned) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Data setelah pembersihan terlalu sedikit (hanya {len(df_cleaned)} baris). "
                   "Gagal melanjutkan analisis statistik. Silakan periksa kembali dataset Anda."
        )
        
    return df_cleaned, logs
