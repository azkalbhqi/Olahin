from typing import Dict, Any, List

def generate_narrative_interpretation(
    normality_results: Dict[str, Any],
    analysis_results: Dict[str, Any],
    independent_vars: List[str],
    dependent_var: str,
    group_var: str = None
) -> str:
    """
    Generates natural language interpretation in Indonesian based on statistical results.
    """
    model_type = analysis_results["model_type"]
    is_normal = normality_results["is_normal"]
    norm_test = normality_results["test_name"]
    norm_p = normality_results["p_value"]
    
    # 1. Normality & Routing Narrative
    norm_desc = (
        f"Berdasarkan Uji Normalitas menggunakan metode {norm_test} pada variabel '{dependent_var}', "
        f"diperoleh nilai p-value sebesar {norm_p:.4f}. "
    )
    if is_normal:
        norm_desc += (
            f"Karena p-value \u2265 0.05, data dinyatakan berdistribusi normal. "
            f"Oleh karena itu, sistem mengarahkan analisis ke metode Parametrik, yaitu **{model_type}**."
        )
    else:
        norm_desc += (
            f"Karena p-value < 0.05, data dinyatakan tidak berdistribusi normal. "
            f"Oleh karena itu, sistem dialihkan ke metode Non-Parametrik, yaitu **{model_type}**."
        )
        
    narrative_parts = [norm_desc]

    # 2. Main Test Narrative
    if model_type == "Multiple Linear Regression":
        metrics = analysis_results["metrics"]
        r2 = metrics["r_squared"]
        r2_pct = r2 * 100
        f_p = metrics["p_value"]
        coefs = analysis_results["coefficients"]
        
        # Simultan
        if f_p < 0.05:
            simultan_desc = (
                f"Secara **simultan** (keseluruhan), model regresi ini dinyatakan **signifikan** (p-value = {f_p:.4f} < 0.05). "
                f"Variabel independen ({', '.join(independent_vars)}) berpengaruh secara nyata terhadap variabel dependen '{dependent_var}'. "
                f"Model ini memiliki nilai Koefisien Determinasi ($R^2 = {r2:.4f}$), yang menunjukkan bahwa kombinasi variabel independen "
                f"mampu menjelaskan variasi pada '{dependent_var}' sebesar **{r2_pct:.1f}%**, sedangkan sisanya sebesar {100-r2_pct:.1f}% "
                f"dijelaskan oleh faktor lain di luar model."
            )
        else:
            simultan_desc = (
                f"Secara **simultan**, model regresi dinyatakan **tidak signifikan** (p-value = {f_p:.4f} \u2265 0.05). "
                f"Artinya, tidak terdapat pengaruh yang nyata secara bersama-sama dari variabel independen "
                f"({', '.join(independent_vars)}) terhadap variabel dependen '{dependent_var}'."
            )
        narrative_parts.append(simultan_desc)
        
        # Parsial
        partial_desc_list = ["Secara **parsial** (masing-masing variabel):"]
        for var in independent_vars:
            if var in coefs:
                c_info = coefs[var]
                coef = c_info["coefficient"]
                p_val = c_info["p_value"]
                direction = "positif" if coef > 0 else "negatif"
                sig_text = "signifikan" if p_val < 0.05 else "tidak signifikan"
                
                effect_desc = (
                    f"- Variabel **{var}** memiliki pengaruh {direction} dan {sig_text} terhadap '{dependent_var}' "
                    f"(koefisien arah \u03b2 = {coef:.4f}, p-value = {p_val:.4f}). "
                )
                
                if p_val < 0.05:
                    effect_desc += (
                        f"Setiap peningkatan satu satuan pada '{var}' akan meningkatkan "
                        if coef > 0 else 
                        f"Setiap peningkatan satu satuan pada '{var}' akan menurunkan "
                    )
                    effect_desc += f"'{dependent_var}' sebesar {abs(coef):.4f} satuan, dengan asumsi variabel lain konstan."
                else:
                    effect_desc += f"Variasi pada '{var}' tidak memiliki bukti empiris yang cukup untuk mempengaruhi '{dependent_var}' secara nyata."
                    
                partial_desc_list.append(effect_desc)
                
        narrative_parts.append("\n".join(partial_desc_list))

    elif model_type == "Spearman Rank Correlation":
        results = analysis_results["results"]
        correlation_details = ["Hasil uji korelasi Spearman menunjukkan hubungan berikut:"]
        
        for var, res in results.items():
            rho = res["correlation_coefficient"]
            p_val = res["p_value"]
            strength = res["strength"]
            direction = res["direction"]
            is_sig = res["is_significant"]
            
            sig_text = "signifikan" if is_sig else "tidak signifikan"
            dir_text = "searah (positif)" if direction == "positif" else "berlawanan arah (negatif)"
            
            detail = (
                f"- Hubungan antara **{var}** dengan **{dependent_var}** bernilai **{sig_text}** (p-value = {p_val:.4f}). "
                f"Kekuatan korelasi tergolong **{strength}** dengan koefisien korelasi (\u03c1 = {rho:.4f}) "
                f"dan arah hubungan yang {dir_text}. "
            )
            
            if is_sig:
                if rho > 0:
                    detail += f"Artinya, semakin tinggi nilai '{var}', maka nilai '{dependent_var}' cenderung semakin meningkat."
                else:
                    detail += f"Artinya, semakin tinggi nilai '{var}', maka nilai '{dependent_var}' cenderung semakin menurun."
            else:
                detail += f"Artinya, tidak terdapat hubungan yang cukup kuat secara statistik antara '{var}' dan '{dependent_var}'."
                
            correlation_details.append(detail)
            
        narrative_parts.append("\n".join(correlation_details))

    elif model_type == "Independent Samples T-Test":
        metrics = analysis_results["metrics"]
        p_val = metrics["p_value"]
        is_sig = metrics["is_significant"]
        groups = analysis_results["groups"]
        
        g1 = groups["group1"]
        g2 = groups["group2"]
        
        diff_desc = (
            f"Berdasarkan Uji T-Test Independen, diperoleh nilai p-value sebesar {p_val:.4f}. "
        )
        
        if is_sig:
            diff_desc += f"Karena p-value < 0.05, maka **Hipotesis (H1) Diterima** (ada perbedaan signifikan). "
            if g1["mean"] > g2["mean"]:
                diff_desc += (
                    f"Rata-rata kelompok **{g1['label']}** (Mean = {g1['mean']:.4f}, N = {g1['count']}) "
                    f"secara signifikan lebih tinggi daripada kelompok **{g2['label']}** (Mean = {g2['mean']:.4f}, N = {g2['count']})."
                )
            else:
                diff_desc += (
                    f"Rata-rata kelompok **{g2['label']}** (Mean = {g2['mean']:.4f}, N = {g2['count']}) "
                    f"secara signifikan lebih tinggi daripada kelompok **{g1['label']}** (Mean = {g1['mean']:.4f}, N = {g1['count']})."
                )
        else:
            diff_desc += (
                f"Karena p-value \u2265 0.05, maka **Hipotesis Nol (H0) Diterima** (tidak ada perbedaan signifikan). "
                f"Rata-rata kelompok **{g1['label']}** (Mean = {g1['mean']:.4f}, N = {g1['count']}) dan kelompok "
                f"**{g2['label']}** (Mean = {g2['mean']:.4f}, N = {g2['count']}) secara statistik dianggap sama / tidak berbeda nyata."
            )
        narrative_parts.append(diff_desc)

    elif model_type == "Mann-Whitney U Test":
        metrics = analysis_results["metrics"]
        p_val = metrics["p_value"]
        is_sig = metrics["is_significant"]
        groups = analysis_results["groups"]
        
        g1 = groups["group1"]
        g2 = groups["group2"]
        
        diff_desc = (
            f"Berdasarkan Uji Mann-Whitney U, diperoleh nilai p-value sebesar {p_val:.4f}. "
        )
        
        if is_sig:
            diff_desc += f"Karena p-value < 0.05, maka **Hipotesis (H1) Diterima** (ada perbedaan nilai median yang signifikan). "
            if g1["median"] > g2["median"]:
                diff_desc += (
                    f"Kelompok **{g1['label']}** (Median = {g1['median']:.4f}, N = {g1['count']}) memiliki nilai "
                    f"median yang signifikan lebih tinggi dibandingkan kelompok **{g2['label']}** (Median = {g2['median']:.4f}, N = {g2['count']})."
                )
            else:
                diff_desc += (
                    f"Kelompok **{g2['label']}** (Median = {g2['median']:.4f}, N = {g2['count']}) memiliki nilai "
                    f"median yang signifikan lebih tinggi dibandingkan kelompok **{g1['label']}** (Median = {g1['median']:.4f}, N = {g1['count']})."
                )
        else:
            diff_desc += (
                f"Karena p-value \u2265 0.05, maka **Hipotesis Nol (H0) Diterima** (tidak ada perbedaan median yang signifikan). "
                f"Distribusi nilai kelompok **{g1['label']}** (Median = {g1['median']:.4f}, N = {g1['count']}) dan "
                f"kelompok **{g2['label']}** (Median = {g2['median']:.4f}, N = {g2['count']}) secara statistik dianggap setara."
            )
        narrative_parts.append(diff_desc)

    # 3. Final Conclusion
    conclusion = (
        "\n**Kesimpulan Akhir:** "
    )
    main_sig = False
    if "is_model_significant" in analysis_results.get("metrics", {}):
        main_sig = analysis_results["metrics"]["is_model_significant"]
    elif "is_significant" in analysis_results.get("metrics", {}):
        main_sig = analysis_results["metrics"]["is_significant"]
        
    if main_sig:
        conclusion += f"Hipotesis penelitian (H1) Diterima. Terdapat hubungan/pengaruh/perbedaan yang signifikan pada variabel yang dianalisis."
    else:
        conclusion += f"Hipotesis penelitian (H1) Ditolak (H0 Diterima). Tidak cukup bukti statistik untuk menyatakan hubungan/pengaruh/perbedaan pada variabel yang dianalisis."
        
    narrative_parts.append(conclusion)

    return "\n\n".join(narrative_parts)
