import pandas as pd
import numpy as np
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import lilliefors
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from typing import List, Dict, Any, Tuple
from fastapi import HTTPException
import itertools

# --- 1. Instrument Validation Module (FR-03) ---
def run_instrument_validation(df: pd.DataFrame, items: List[str]) -> Dict[str, Any]:
    """
    Runs validity (corrected item-total correlation) and reliability (Cronbach's Alpha) tests.
    """
    if len(items) < 2:
        return {
            "is_applicable": False,
            "message": "Uji validitas dan reliabilitas memerlukan minimal 2 variabel/item instrumen."
        }
        
    df_items = df[items].apply(pd.to_numeric, errors='coerce').dropna()
    N = len(df_items)
    
    if N < 5:
        return {
            "is_applicable": False,
            "message": "Data tidak cukup (N < 5) untuk melakukan uji validitas dan reliabilitas."
        }
        
    # 1. Reliability Test: Cronbach's Alpha
    k = len(items)
    item_vars = df_items.var(ddof=1)
    total_var = df_items.sum(axis=1).var(ddof=1)
    
    if total_var == 0:
        cronbach_alpha = 0.0
    else:
        cronbach_alpha = (k / (k - 1)) * (1.0 - (item_vars.sum() / total_var))
        
    is_reliable = bool(cronbach_alpha >= 0.6)
    
    # 2. Validity Test: Corrected Item-Total Correlation (Pearson)
    validity_results = {}
    all_valid = True
    
    for item in items:
        other_items = [v for v in items if v != item]
        sum_others = df_items[other_items].sum(axis=1)
        r_val, p_val = stats.pearsonr(df_items[item], sum_others)
        
        if np.isnan(r_val):
            r_val = 0.0
        if np.isnan(p_val):
            p_val = 1.0
            
        is_valid = bool(r_val >= 0.3)
        if not is_valid:
            all_valid = False
            
        validity_results[item] = {
            "correlation_coefficient": float(r_val),
            "p_value": float(p_val),
            "is_valid": is_valid
        }
        
    return {
        "is_applicable": True,
        "sample_size": N,
        "reliability": {
            "cronbach_alpha": float(cronbach_alpha),
            "is_reliable": is_reliable,
            "threshold": 0.6
        },
        "validity": {
            "items": validity_results,
            "all_items_valid": all_valid,
            "threshold": 0.3
        }
    }

# --- 2. Sample Size & Normality Router (FR-04, FR-06) ---
def run_normality_check(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    """
    Performs normality testing based on sample size:
    - N < 30: Shapiro-Wilk Test
    - N >= 30: Kolmogorov-Smirnov Test with Lilliefors correction
    """
    data = pd.to_numeric(df[col], errors='coerce').dropna()
    N = len(data)
    
    if N < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran sampel ({N}) terlalu kecil untuk melakukan uji normalitas pada kolom '{col}'."
        )
        
    if N < 30:
        stat, p_val = stats.shapiro(data)
        test_name = "Shapiro-Wilk"
    else:
        stat, p_val = lilliefors(data, dist='norm')
        test_name = "Kolmogorov-Smirnov (Lilliefors)"
        
    if np.isnan(p_val):
        p_val = 0.0
        
    is_normal = bool(p_val >= 0.05)
    
    return {
        "test_name": test_name,
        "sample_size": N,
        "statistic": float(stat),
        "p_value": float(p_val),
        "is_normal": is_normal
    }

# --- 3. Descriptive Statistics Module (FR-06b) ---
def run_descriptive_analysis(df: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
    """
    Computes summary statistics for the specified columns.
    """
    results = {}
    for col in columns:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(series) == 0:
            continue
            
        mode_series = series.mode()
        mode_val = float(mode_series.iloc[0]) if not mode_series.empty else float(series.median())
        
        results[col] = {
            "mean": float(series.mean()),
            "median": float(series.median()),
            "mode": mode_val,
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "variance": float(series.var()) if len(series) > 1 else 0.0,
            "range": float(series.max() - series.min()),
            "min": float(series.min()),
            "max": float(series.max()),
            "count": int(len(series))
        }
    return results

# --- 4. Time-Series Decision Engine (FR-05) ---
def run_time_series_path(df: pd.DataFrame, dependent_var: str, independent_vars: List[str] = None, time_col: str = None) -> Dict[str, Any]:
    """
    Executes Time-Series analysis:
    1. Check stationarity on dependent variable (ADF + KPSS).
    2. If not stationary, apply differencing (up to d=2).
    3. Fit ARIMA (univariate) or VAR (multivariate) model.
    """
    # Sort by time_col if provided
    if time_col and time_col in df.columns:
        df_ts = df.sort_values(by=time_col).copy()
    else:
        df_ts = df.copy()
        
    series = pd.to_numeric(df_ts[dependent_var], errors='coerce').dropna()
    N = len(series)
    
    if N < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran sampel ({N}) terlalu kecil untuk analisis Time-Series. Minimal 10 baris."
        )
        
    # Helper to check stationarity
    def check_stationarity(s):
        # ADF Test
        try:
            adf_stat, adf_p, *_, adf_crit, _ = stats.tsa.stattools.adfuller(s)
            adf_stationary = adf_p < 0.05
        except Exception:
            adf_p, adf_stationary = 1.0, False
            
        # KPSS Test
        try:
            kpss_stat, kpss_p, *_ = stats.tsa.stattools.kpss(s, regression='c', nlags="auto")
            kpss_stationary = kpss_p >= 0.05
        except Exception:
            kpss_p, kpss_stationary = 0.0, False
            
        # Cross-validation
        is_stationary = adf_stationary and kpss_stationary
        return is_stationary, adf_p, kpss_p
        
    # Stationarity loop (differencing)
    d = 0
    work_series = series.copy()
    stationarity_log = []
    
    is_stat, adf_p, kpss_p = check_stationarity(work_series)
    stationarity_log.append({
        "differencing_degree": d,
        "adf_p_value": float(adf_p),
        "kpss_p_value": float(kpss_p),
        "is_stationary": is_stat
    })
    
    while not is_stat and d < 2:
        d += 1
        work_series = work_series.diff().dropna()
        is_stat, adf_p, kpss_p = check_stationarity(work_series)
        stationarity_log.append({
            "differencing_degree": d,
            "adf_p_value": float(adf_p),
            "kpss_p_value": float(kpss_p),
            "is_stationary": is_stat
        })
        
    # Model Fitting
    model_type = ""
    fitted_model_results = {}
    forecasts = []
    
    is_multivariate = independent_vars and len(independent_vars) > 0
    
    if not is_multivariate:
        # Univariate: ARIMA(p, d, q) grid search
        model_type = "ARIMA"
        best_aic = float('inf')
        best_order = (0, d, 0)
        best_fit = None
        
        # Grid search over p and q
        for p in [0, 1, 2]:
            for q in [0, 1, 2]:
                try:
                    # Fit on original series specifying order (p, d, q)
                    model = sm.tsa.ARIMA(series, order=(p, d, q))
                    fit = model.fit()
                    if fit.aic < best_aic:
                        best_aic = fit.aic
                        best_order = (p, d, q)
                        best_fit = fit
                except Exception:
                    continue
                    
        if best_fit is not None:
            forecast_objs = best_fit.forecast(steps=5)
            forecasts = forecast_objs.tolist()
            
            # Extract coefficients
            coefs = {}
            for name, val in best_fit.params.items():
                coefs[name] = float(val)
                
            fitted_model_results = {
                "order": best_order,
                "aic": float(best_fit.aic),
                "bic": float(best_fit.bic),
                "coefficients": coefs,
                "p_values": {name: float(p) for name, p in best_fit.pvalues.items()}
            }
        else:
            raise HTTPException(status_code=400, detail="Gagal melatih model ARIMA pada data deret waktu Anda.")
    else:
        # Multivariate: VAR
        model_type = "VAR (Vector Autoregression)"
        all_cols = [dependent_var] + independent_vars
        df_ts_clean = df_ts[all_cols].apply(pd.to_numeric, errors='coerce').dropna()
        
        # Apply same differencing degree
        if d > 0:
            df_ts_diff = df_ts_clean.diff(d).dropna()
        else:
            df_ts_diff = df_ts_clean
            
        try:
            model = sm.tsa.VAR(df_ts_diff)
            # Automatic lag selection based on AIC
            results = model.fit(maxlags=min(3, len(df_ts_diff) // 5))
            
            # Forecast next 5 steps
            lag_order = results.k_ar
            forecast_matrix = results.forecast(df_ts_diff.values[-lag_order:], steps=5)
            
            # Extract dependent variable forecasts (first column)
            forecasts = forecast_matrix[:, 0].tolist()
            
            fitted_model_results = {
                "lags_selected": int(lag_order),
                "aic": float(results.aic),
                "bic": float(results.bic),
                "equations_parameters": {
                    col: {coef_name: float(coef_val) for coef_name, coef_val in results.params[col].items()}
                    for col in all_cols
                }
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal melatih model VAR: {str(e)}")
            
    return {
        "model_type": model_type,
        "differencing_degree": d,
        "is_stationary_final": is_stat,
        "stationarity_log": stationarity_log,
        "model_details": fitted_model_results,
        "forecasts_5_steps": forecasts
    }

# --- 5. Effect Size Helpers (FR-11) ---
def compute_cohens_d_ind(g1_data, g2_data) -> float:
    n1, n2 = len(g1_data), len(g2_data)
    v1, v2 = g1_data.var(ddof=1), g2_data.var(ddof=1)
    if n1 + n2 - 2 <= 0:
        return 0.0
    pooled_std = np.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return float((g1_data.mean() - g2_data.mean()) / pooled_std)

def compute_cohens_d_paired(g1_data, g2_data) -> float:
    diff = g1_data - g2_data
    std_diff = diff.std(ddof=1)
    if std_diff == 0:
        return 0.0
    return float(diff.mean() / std_diff)

def compute_rank_r(p_value, N) -> float:
    # Approximate standard normal Z score from two-tailed p-value
    if p_value == 0:
        p_value = 1e-15
    z = abs(stats.norm.ppf(p_value / 2.0))
    return float(z / np.sqrt(N))

def compute_epsilon_squared(h_stat, N) -> float:
    if N**2 - 1 == 0:
        return 0.0
    return float(h_stat * (N + 1) / (N**2 - 1))

# --- 6. Cross-Sectional Routing & Engines ---
def execute_comparative(df: pd.DataFrame, dependent_var: str, group_var: str, is_paired: bool, is_normal: bool, alpha: float) -> Dict[str, Any]:
    """
    Executes comparison path (T-test, Mann-Whitney U, Wilcoxon, ANOVA, Kruskal-Wallis)
    """
    groups = df[group_var].unique()
    num_groups = len(groups)
    
    if num_groups < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Variabel grup '{group_var}' harus memiliki minimal 2 kelompok. Ditemukan: {list(groups)}"
        )
        
    # Minimum Sample Size Guard per group
    for g in groups:
        g_len = len(df[df[group_var] == g])
        if g_len < 5:
            raise HTTPException(
                status_code=400,
                detail=f"Kelompok '{g}' hanya memiliki {g_len} data. Diperlukan minimal 5 data per kelompok untuk uji statistik yang valid."
            )
            
    if num_groups == 2:
        g1_lbl, g2_lbl = groups[0], groups[1]
        
        if is_paired:
            # Paired requires equal lengths
            g1_data = df[df[group_var] == g1_lbl].sort_index()
            g2_data = df[df[group_var] == g2_lbl].sort_index()
            
            # Sync length by index position mapping or just check equal lengths
            if len(g1_data) != len(g2_data):
                # Attempt to align by index
                common_idx = g1_data.index.intersection(g2_data.index)
                if len(common_idx) >= 5:
                    g1_data = g1_data.loc[common_idx]
                    g2_data = g2_data.loc[common_idx]
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Data berpasangan memerlukan jumlah baris yang sama untuk tiap kelompok. "
                               f"Kelompok '{g1_lbl}' memiliki {len(g1_data)} baris, sedangkan '{g2_lbl}' memiliki {len(g2_data)} baris."
                    )
            
            g1_vals = pd.to_numeric(g1_data[dependent_var], errors='coerce').dropna()
            g2_vals = pd.to_numeric(g2_data[dependent_var], errors='coerce').dropna()
            
            if is_normal:
                stat, p_val = stats.ttest_rel(g1_vals, g2_vals)
                model_name = "Paired Samples T-Test"
                effect_size_name = "Cohen's d"
                effect_size_val = compute_cohens_d_paired(g1_vals, g2_vals)
            else:
                stat, p_val = stats.wilcoxon(g1_vals, g2_vals)
                model_name = "Wilcoxon Signed-Rank Test"
                effect_size_name = "r (Z/sqrt(N))"
                effect_size_val = compute_rank_r(p_val, len(g1_vals) * 2)
                
            g1_mean, g2_mean = float(g1_vals.mean()), float(g2_vals.mean())
            g1_med, g2_med = float(g1_vals.median()), float(g2_vals.median())
            
            return {
                "model_type": model_name,
                "is_parametric": is_normal,
                "groups": {
                    "group1": {"label": str(g1_lbl), "mean": g1_mean, "median": g1_med, "count": len(g1_vals)},
                    "group2": {"label": str(g2_lbl), "mean": g2_mean, "median": g2_med, "count": len(g2_vals)}
                },
                "metrics": {
                    "statistic": float(stat),
                    "p_value": float(p_val),
                    "is_significant": bool(p_val < alpha),
                    "effect_size_name": effect_size_name,
                    "effect_size": float(effect_size_val)
                }
            }
        else:
            # Independent 2 Groups
            g1_vals = pd.to_numeric(df[df[group_var] == g1_lbl][dependent_var], errors='coerce').dropna()
            g2_vals = pd.to_numeric(df[df[group_var] == g2_lbl][dependent_var], errors='coerce').dropna()
            
            if is_normal:
                stat, p_val = stats.ttest_ind(g1_vals, g2_vals, equal_var=False) # Welch's T-Test
                model_name = "Independent Samples T-Test"
                effect_size_name = "Cohen's d"
                effect_size_val = compute_cohens_d_ind(g1_vals, g2_vals)
            else:
                stat, p_val = stats.mannwhitneyu(g1_vals, g2_vals, alternative='two-sided')
                model_name = "Mann-Whitney U Test"
                effect_size_name = "r (Z/sqrt(N))"
                effect_size_val = compute_rank_r(p_val, len(g1_vals) + len(g2_vals))
                
            g1_mean, g2_mean = float(g1_vals.mean()), float(g2_vals.mean())
            g1_med, g2_med = float(g1_vals.median()), float(g2_vals.median())
            
            return {
                "model_type": model_name,
                "is_parametric": is_normal,
                "groups": {
                    "group1": {"label": str(g1_lbl), "mean": g1_mean, "median": g1_med, "count": len(g1_vals)},
                    "group2": {"label": str(g2_lbl), "mean": g2_mean, "median": g2_med, "count": len(g2_vals)}
                },
                "metrics": {
                    "statistic": float(stat),
                    "p_value": float(p_val),
                    "is_significant": bool(p_val < alpha),
                    "effect_size_name": effect_size_name,
                    "effect_size": float(effect_size_val)
                }
            }
    else:
        # > 2 Groups (ANOVA / Kruskal-Wallis)
        group_data = [pd.to_numeric(df[df[group_var] == g][dependent_var], errors='coerce').dropna().values for g in groups]
        total_n = sum(len(g) for g in group_data)
        
        # Means and Medians per group
        group_summaries = {}
        for g in groups:
            vals = pd.to_numeric(df[df[group_var] == g][dependent_var], errors='coerce').dropna()
            group_summaries[str(g)] = {
                "mean": float(vals.mean()),
                "median": float(vals.median()),
                "count": len(vals)
            }
            
        if is_normal:
            stat, p_val = stats.f_oneway(*group_data)
            model_name = "One-Way ANOVA"
            
            # Calculate Eta-squared
            grand_mean = np.mean(np.concatenate(group_data))
            ss_total = np.sum([(x - grand_mean)**2 for g in group_data for x in g])
            ss_between = np.sum([len(g) * (np.mean(g) - grand_mean)**2 for g in group_data])
            eta_sq = ss_between / ss_total if ss_total != 0 else 0.0
            
            effect_size_name = "Eta-squared"
            effect_size_val = eta_sq
            
            # Post-hoc: Tukey HSD (mandatory)
            posthoc = []
            if p_val < alpha:
                try:
                    cleaned_df = df[[group_var, dependent_var]].dropna()
                    cleaned_df[dependent_var] = pd.to_numeric(cleaned_df[dependent_var], errors='coerce')
                    cleaned_df = cleaned_df.dropna()
                    
                    tukey = pairwise_tukeyhsd(cleaned_df[dependent_var], cleaned_df[group_var], alpha=alpha)
                    for row in tukey.summary().data[1:]:
                        posthoc.append({
                            "group1": str(row[0]),
                            "group2": str(row[1]),
                            "mean_diff": float(row[2]),
                            "p_value_corrected": float(row[3]),
                            "is_significant": bool(row[5])
                        })
                except Exception:
                    pass
        else:
            stat, p_val = stats.kruskal(*group_data)
            model_name = "Kruskal-Wallis Test"
            
            # Epsilon-squared
            eps_sq = compute_epsilon_squared(stat, total_n)
            effect_size_name = "Epsilon-squared"
            effect_size_val = eps_sq
            
            # Post-hoc: Pairwise Mann-Whitney with Bonferroni correction
            posthoc = []
            if p_val < alpha:
                group_pairs = list(itertools.combinations(groups, 2))
                num_comparisons = len(group_pairs)
                for g1, g2 in group_pairs:
                    g1_vals = pd.to_numeric(df[df[group_var] == g1][dependent_var], errors='coerce').dropna()
                    g2_vals = pd.to_numeric(df[df[group_var] == g2][dependent_var], errors='coerce').dropna()
                    u_stat, mw_p = stats.mannwhitneyu(g1_vals, g2_vals, alternative='two-sided')
                    
                    p_corrected = min(mw_p * num_comparisons, 1.0)
                    posthoc.append({
                        "group1": str(g1),
                        "group2": str(g2),
                        "mean_diff": float(g1_vals.mean() - g2_vals.mean()),
                        "p_value_corrected": float(p_corrected),
                        "is_significant": bool(p_corrected < alpha)
                    })
                    
        return {
            "model_type": model_name,
            "is_parametric": is_normal,
            "groups_summary": group_summaries,
            "metrics": {
                "statistic": float(stat),
                "p_value": float(p_val),
                "is_significant": bool(p_val < alpha),
                "effect_size_name": effect_size_name,
                "effect_size": float(effect_size_val)
            },
            "post_hoc_results": posthoc if p_val < alpha else []
        }

def execute_associative(df: pd.DataFrame, dependent_var: str, independent_vars: List[str], alpha: float) -> Dict[str, Any]:
    """
    Executes regression path.
    If multiple independent variables, checks multicollinearity (VIF).
    If any VIF > 10, drops the highest VIF and checks again.
    """
    y = pd.to_numeric(df[dependent_var], errors='coerce')
    
    # Clean and filter predictors
    active_predictors = [var for var in independent_vars if var in df.columns]
    
    if len(active_predictors) == 0:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada variabel independen valid yang ditemukan untuk melakukan analisis pengaruh."
        )
        
    vif_log = []
    
    # Multicollinearity check (VIF loop) for > 1 predictors
    while len(active_predictors) > 1:
        X = df[active_predictors].apply(pd.to_numeric, errors='coerce')
        X_with_const = sm.add_constant(X)
        
        # Calculate VIF
        vifs = {}
        for i, var in enumerate(active_predictors):
            # index 0 is const in add_constant output
            try:
                vifs[var] = variance_inflation_factor(X_with_const.values, i + 1)
            except Exception:
                vifs[var] = 999.0 # flag for perfect collinearity
                
        max_var = max(vifs, key=vifs.get)
        max_vif = vifs[max_var]
        
        if max_vif > 10.0:
            vif_log.append(
                f"Mendeteksi multikolinearitas: Variabel '{max_var}' memiliki VIF = {max_vif:.2f} (> 10.0). Variabel ini dieliminasi."
            )
            active_predictors.remove(max_var)
        else:
            break
            
    # Fit regression model
    X_final = df[active_predictors].apply(pd.to_numeric, errors='coerce')
    X_final_const = sm.add_constant(X_final)
    
    try:
        model = sm.OLS(y, X_final_const).fit()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal melakukan estimasi model regresi: {str(e)}"
        )
        
    r_squared = float(model.rsquared)
    adj_r_squared = float(model.rsquared_adj)
    f_stat = float(model.fvalue)
    f_pvalue = float(model.f_pvalue) if not np.isnan(model.f_pvalue) else 0.0
    
    coefs = {}
    variables_log = []
    
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
            "is_significant": bool(p_val < alpha)
        }
        
        if var != "const":
            direction = "positif" if coef > 0 else "negatif"
            sig_text = "signifikan" if p_val < alpha else "tidak signifikan"
            variables_log.append(
                f"Variabel '{var}' berpengaruh {direction} dan {sig_text} (koefisien={coef:.4f}, p-value={p_val:.4f})."
            )
            
    model_name = "Simple Linear Regression" if len(active_predictors) == 1 else "Multiple Linear Regression"
    
    return {
        "model_type": model_name,
        "is_parametric": True,
        "final_predictors": active_predictors,
        "vif_eliminations": vif_log,
        "metrics": {
            "r_squared": r_squared,
            "adjusted_r_squared": adj_r_squared,
            "f_statistic": f_stat,
            "p_value": f_pvalue,
            "is_model_significant": bool(f_pvalue < alpha)
        },
        "coefficients": coefs,
        "variables_log": variables_log
    }

def execute_correlation(df: pd.DataFrame, dependent_var: str, independent_vars: List[str], is_normal: bool, alpha: float) -> Dict[str, Any]:
    """
    Executes correlation path (Pearson if normal, Spearman if non-normal).
    """
    y = pd.to_numeric(df[dependent_var], errors='coerce')
    results = {}
    model_significant = False
    
    model_type = "Pearson Correlation" if is_normal else "Spearman Rank Correlation"
    
    for var in independent_vars:
        if var not in df.columns:
            continue
        x = pd.to_numeric(df[var], errors='coerce')
        
        if is_normal:
            coeff, p_val = stats.pearsonr(x, y)
        else:
            coeff, p_val = stats.spearmanr(x, y)
            
        if np.isnan(coeff): coeff = 0.0
        if np.isnan(p_val): p_val = 1.0
        
        is_sig = bool(p_val < alpha)
        if is_sig:
            model_significant = True
            
        # Strength description
        abs_coeff = abs(coeff)
        if abs_coeff < 0.2:
            strength = "sangat lemah"
        elif abs_coeff < 0.4:
            strength = "lemah"
        elif abs_coeff < 0.6:
            strength = "sedang"
        elif abs_coeff < 0.8:
            strength = "kuat"
        else:
            strength = "sangat kuat"
            
        direction = "positif" if coeff > 0 else "negatif"
        
        results[var] = {
            "correlation_coefficient": float(coeff),
            "p_value": float(p_val),
            "is_significant": is_sig,
            "strength": strength,
            "direction": direction
        }
        
    return {
        "model_type": model_type,
        "is_parametric": is_normal,
        "results": results,
        "metrics": {
            "is_model_significant": bool(model_significant),
            "p_value": min([res["p_value"] for res in results.values()]) if results else 1.0
        }
    }

def execute_mediation(df: pd.DataFrame, dependent_var: str, independent_vars: List[str], mediator_var: str, alpha: float) -> Dict[str, Any]:
    """
    Executes simple path analysis (stepwise OLS regression) + Sobel Test.
    Model: X -> M -> Y.
    """
    if not mediator_var:
        raise HTTPException(
            status_code=400,
            detail="Variabel mediator (mediator_var) wajib ditentukan untuk analisis mediasi."
        )
        
    if mediator_var not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Variabel mediator '{mediator_var}' tidak ditemukan dalam dataset."
        )
        
    if len(independent_vars) == 0:
        raise HTTPException(
            status_code=400,
            detail="Variabel independen (X) wajib dipilih untuk analisis mediasi."
        )
        
    x_var = independent_vars[0] # simple mediation handles single X
    X = pd.to_numeric(df[x_var], errors='coerce')
    M = pd.to_numeric(df[mediator_var], errors='coerce')
    Y = pd.to_numeric(df[dependent_var], errors='coerce')
    
    # Path a: X -> M
    X_const = sm.add_constant(X)
    model_a = sm.OLS(M, X_const).fit()
    coef_a = float(model_a.params[x_var])
    se_a = float(model_a.bse[x_var])
    p_a = float(model_a.pvalues[x_var])
    
    # Path b & c': X + M -> Y
    XM = pd.concat([X, M], axis=1)
    XM_const = sm.add_constant(XM)
    model_b = sm.OLS(Y, XM_const).fit()
    coef_b = float(model_b.params[mediator_var])
    se_b = float(model_b.bse[mediator_var])
    p_b = float(model_b.pvalues[mediator_var])
    
    coef_c_prime = float(model_b.params[x_var])
    p_c_prime = float(model_b.pvalues[x_var])
    
    # Path c: X -> Y (Total effect)
    model_c = sm.OLS(Y, X_const).fit()
    coef_c = float(model_c.params[x_var])
    p_c = float(model_c.pvalues[x_var])
    
    # Sobel Test Calculation
    # Z = (a * b) / sqrt(b^2 * sa^2 + a^2 * sb^2)
    denominator = np.sqrt((coef_b**2 * se_a**2) + (coef_a**2 * se_b**2))
    indirect_effect = coef_a * coef_b
    
    if denominator == 0:
        sobel_z = 0.0
        sobel_p = 1.0
    else:
        sobel_z = indirect_effect / denominator
        sobel_p = 2 * (1 - stats.norm.cdf(abs(sobel_z)))
        
    is_indirect_sig = bool(sobel_p < alpha)
    
    return {
        "model_type": "Path Analysis (Simple Mediation)",
        "independent_var": x_var,
        "mediator_var": mediator_var,
        "dependent_var": dependent_var,
        "paths": {
            "path_a": {"coefficient": coef_a, "std_err": se_a, "p_value": p_a, "is_significant": bool(p_a < alpha)},
            "path_b": {"coefficient": coef_b, "std_err": se_b, "p_value": p_b, "is_significant": bool(p_b < alpha)},
            "path_c_prime": {"coefficient": coef_c_prime, "p_value": p_c_prime, "is_significant": bool(p_c_prime < alpha)},
            "total_effect_c": {"coefficient": coef_c, "p_value": p_c, "is_significant": bool(p_c < alpha)}
        },
        "sobel_test": {
            "statistic_z": float(sobel_z),
            "p_value": float(sobel_p),
            "indirect_effect": float(indirect_effect),
            "is_significant": is_indirect_sig
        }
    }

# --- 7. Main Router & Orchestrator ---
def execute_routing_and_analysis(
    df: pd.DataFrame,
    analysis_goal: str,
    independent_vars: List[str],
    dependent_var: str,
    group_var: str = None,
    is_paired: bool = False,
    mediator_var: str = None,
    alpha: float = 0.05
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Determines normal distribution routing and executes the appropriate statistical test.
    
    Returns:
        normality_results: Dict
        analysis_results: Dict
    """
    # 1. Normality Test on Dependent Variable
    normality_res = run_normality_check(df, dependent_var)
    is_normal = normality_res["is_normal"]
    
    # 2. Routing based on analysis_goal
    if analysis_goal == "komparasi":
        analysis_res = execute_comparative(df, dependent_var, group_var, is_paired, is_normal, alpha)
    elif analysis_goal == "pengaruh":
        analysis_res = execute_associative(df, dependent_var, independent_vars, alpha)
    elif analysis_goal == "korelasi":
        analysis_res = execute_correlation(df, dependent_var, independent_vars, is_normal, alpha)
    elif analysis_goal == "mediasi_moderasi":
        analysis_res = execute_mediation(df, dependent_var, independent_vars, mediator_var, alpha)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tujuan analisis '{analysis_goal}' tidak didukung. Gunakan 'komparasi', 'pengaruh', 'korelasi', atau 'mediasi_moderasi'."
        )
        
    return normality_res, analysis_res
