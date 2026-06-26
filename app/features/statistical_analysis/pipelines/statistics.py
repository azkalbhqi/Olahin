import pandas as pd
import numpy as np
import scipy.stats as stats
import statsmodels.api as sm
from typing import List, Dict, Any, Tuple
from fastapi import HTTPException

def run_normality_test(
    df: pd.DataFrame, 
    col: str
) -> Tuple[str, float, float, bool]:
    """
    Performs normality test on the specified column.
    Uses Shapiro-Wilk if N < 50, otherwise Kolmogorov-Smirnov.
    
    Returns:
        test_name: str ("Shapiro-Wilk" or "Kolmogorov-Smirnov")
        statistic: float
        p_value: float
        is_normal: bool (p_value >= 0.05)
    """
    data = df[col].dropna()
    N = len(data)
    
    if N < 3:
        raise HTTPException(
            status_code=400, 
            detail=f"Data pada kolom '{col}' terlalu sedikit untuk diuji normalitasnya (N={N})."
        )
        
    if N < 50:
        stat, p_val = stats.shapiro(data)
        test_name = "Shapiro-Wilk"
    else:
        # For Kolmogorov-Smirnov, test against normal distribution with matching mean and std
        mean = data.mean()
        std = data.std()
        if std == 0:
            stat, p_val = 0.0, 0.0
        else:
            stat, p_val = stats.kstest(data, 'norm', args=(mean, std))
        test_name = "Kolmogorov-Smirnov"
        
    # Handle NaN p-values
    if np.isnan(p_val):
        p_val = 0.0
        
    is_normal = bool(p_val >= 0.05)
    return test_name, float(stat), float(p_val), is_normal

def run_multiple_regression(
    df: pd.DataFrame,
    independent_vars: List[str],
    dependent_var: str
) -> Dict[str, Any]:
    """
    Fits an OLS Multiple Linear Regression model: Y = b0 + b1*X1 + b2*X2 + ...
    """
    X = df[independent_vars]
    y = df[dependent_var]
    
    # Add intercept
    X_with_const = sm.add_constant(X)
    
    try:
        model = sm.OLS(y, X_with_const).fit()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal melakukan Regresi Linear. Hal ini biasanya terjadi jika variabel independen "
                   f"saling berkorelasi sempurna atau tidak bervariasi. Detail: {str(e)}"
        )
        
    # Extract overall metrics
    r_squared = float(model.rsquared)
    adj_r_squared = float(model.rsquared_adj)
    f_stat = float(model.fvalue)
    f_pvalue = float(model.f_pvalue) if not np.isnan(model.f_pvalue) else 0.0
    
    # Extract coefficients details
    coefs = {}
    variables_log = []
    
    # statsmodels index contains 'const' and variables
    for var in model.params.index:
        coef = float(model.params[var])
        se = float(model.bse[var])
        t_stat = float(model.tvalues[var])
        p_val = float(model.pvalues[var])
        
        coefs[var] = {
            "coefficient": coef,
            "std_err": se,
            "t_statistic": t_stat,
            "p_value": p_val,
            "is_significant": bool(p_val < 0.05)
        }
        
        if var != "const":
            direction = "positif" if coef > 0 else "negatif"
            sig_text = "signifikan" if bool(p_val < 0.05) else "tidak signifikan"
            variables_log.append(
                f"Variabel '{var}' berpengaruh {direction} dan {sig_text} (koefisien={coef:.4f}, p-value={p_val:.4f})."
            )
            
    return {
        "model_type": "Multiple Linear Regression",
        "is_parametric": True,
        "metrics": {
            "r_squared": r_squared,
            "adjusted_r_squared": adj_r_squared,
            "f_statistic": f_stat,
            "p_value": f_pvalue,  # Overall model p-value
            "is_model_significant": bool(f_pvalue < 0.05)
        },
        "coefficients": coefs,
        "variables_log": variables_log
    }

def run_spearman_correlation(
    df: pd.DataFrame,
    independent_vars: List[str],
    dependent_var: str
) -> Dict[str, Any]:
    """
    Computes Spearman Rank Correlation between each Independent Variable and the Dependent Variable.
    """
    results = {}
    y = df[dependent_var]
    
    # We will determine the "overall" significance as True if at least one relationship is significant
    model_significant = False
    
    for var in independent_vars:
        x = df[var]
        rho, p_val = stats.spearmanr(x, y)
        
        # Handle NaNs
        if np.isnan(rho): rho = 0.0
        if np.isnan(p_val): p_val = 1.0
        
        is_sig = bool(p_val < 0.05)
        if is_sig:
            model_significant = True
            
        # Strength description
        abs_rho = abs(rho)
        if abs_rho < 0.2:
            strength = "sangat lemah"
        elif abs_rho < 0.4:
            strength = "lemah"
        elif abs_rho < 0.6:
            strength = "sedang"
        elif abs_rho < 0.8:
            strength = "kuat"
        else:
            strength = "sangat kuat"
            
        direction = "positif" if rho > 0 else "negatif"
        
        results[var] = {
            "correlation_coefficient": float(rho),
            "p_value": float(p_val),
            "is_significant": is_sig,
            "strength": strength,
            "direction": direction
        }
        
    return {
        "model_type": "Spearman Rank Correlation",
        "is_parametric": False,
        "results": results,
        "metrics": {
            "is_model_significant": bool(model_significant),
            "p_value": min([res["p_value"] for res in results.values()]) if results else 1.0
        }
    }

def run_t_test(
    df: pd.DataFrame,
    group_var: str,
    dependent_var: str
) -> Dict[str, Any]:
    """
    Performs Independent Samples T-Test (Welch's T-test) between two groups.
    """
    groups = df[group_var].unique()
    if len(groups) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Variabel grup '{group_var}' harus memiliki tepat 2 kategori untuk Uji T-Test. Ditemukan: {list(groups)}"
        )
        
    g1_label, g2_label = groups[0], groups[1]
    g1_data = df[df[group_var] == g1_label][dependent_var]
    g2_data = df[df[group_var] == g2_label][dependent_var]
    
    t_stat, p_val = stats.ttest_ind(g1_data, g2_data, equal_var=False)
    
    if np.isnan(t_stat): t_stat = 0.0
    if np.isnan(p_val): p_val = 1.0
    
    g1_mean = float(g1_data.mean())
    g2_mean = float(g2_data.mean())
    
    return {
        "model_type": "Independent Samples T-Test",
        "is_parametric": True,
        "groups": {
            "group1": {"label": str(g1_label), "mean": g1_mean, "count": len(g1_data)},
            "group2": {"label": str(g2_label), "mean": g2_mean, "count": len(g2_data)}
        },
        "metrics": {
            "t_statistic": float(t_stat),
            "p_value": float(p_val),
            "is_significant": bool(p_val < 0.05)
        }
    }

def run_mann_whitney(
    df: pd.DataFrame,
    group_var: str,
    dependent_var: str
) -> Dict[str, Any]:
    """
    Performs Mann-Whitney U Test between two groups.
    """
    groups = df[group_var].unique()
    if len(groups) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Variabel grup '{group_var}' harus memiliki tepat 2 kategori untuk Uji Mann-Whitney. Ditemukan: {list(groups)}"
        )
        
    g1_label, g2_label = groups[0], groups[1]
    g1_data = df[df[group_var] == g1_label][dependent_var]
    g2_data = df[df[group_var] == g2_label][dependent_var]
    
    u_stat, p_val = stats.mannwhitneyu(g1_data, g2_data, alternative='two-sided')
    
    if np.isnan(u_stat): u_stat = 0.0
    if np.isnan(p_val): p_val = 1.0
    
    g1_median = float(g1_data.median())
    g2_median = float(g2_data.median())
    
    return {
        "model_type": "Mann-Whitney U Test",
        "is_parametric": False,
        "groups": {
            "group1": {"label": str(g1_label), "median": g1_median, "count": len(g1_data)},
            "group2": {"label": str(g2_label), "median": g2_median, "count": len(g2_data)}
        },
        "metrics": {
            "u_statistic": float(u_stat),
            "p_value": float(p_val),
            "is_significant": bool(p_val < 0.05)
        }
    }

def execute_routing_and_analysis(
    df: pd.DataFrame,
    analysis_type: str,
    independent_vars: List[str],
    dependent_var: str,
    group_var: str = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Determines normal distribution routing and executes the appropriate statistical test.
    
    Returns:
        normality_results: Dict
        analysis_results: Dict
    """
    N = len(df)
    
    # 1. Normality Test on Dependent Variable
    test_name, stat, p_val, is_normal = run_normality_test(df, dependent_var)
    normality_results = {
        "test_name": test_name,
        "sample_size": N,
        "statistic": stat,
        "p_value": p_val,
        "is_normal": is_normal
    }
    
    # 2. Decision Routing
    if analysis_type == "Asosiatif":
        if not independent_vars:
            raise HTTPException(
                status_code=400,
                detail="Variabel independen harus diisi untuk analisis Asosiatif."
            )
            
        if is_normal:
            analysis_results = run_multiple_regression(df, independent_vars, dependent_var)
        else:
            analysis_results = run_spearman_correlation(df, independent_vars, dependent_var)
            
    elif analysis_type == "Komparatif":
        if not group_var:
            raise HTTPException(
                status_code=400,
                detail="Variabel grup (group_var) harus diisi untuk analisis Komparatif."
            )
            
        if is_normal:
            analysis_results = run_t_test(df, group_var, dependent_var)
        else:
            analysis_results = run_mann_whitney(df, group_var, dependent_var)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipe analisis '{analysis_type}' tidak didukung. Gunakan 'Asosiatif' atau 'Komparatif'."
        )
        
    return normality_results, analysis_results
