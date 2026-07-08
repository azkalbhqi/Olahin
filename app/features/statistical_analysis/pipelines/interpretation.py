from typing import Dict, Any, List

def generate_narrative_interpretation(
    normality_results: Dict[str, Any],
    analysis_results: Dict[str, Any],
    independent_vars: List[str],
    dependent_var: str,
    group_var: str = None,
    descriptive_stats: Dict[str, Any] = None,
    instrument_validation: Dict[str, Any] = None,
    time_series_results: Dict[str, Any] = None,
    alpha: float = 0.05
) -> str:
    """
    Generates natural language interpretation in Indonesian based on statistical results.
    """
    narrative_parts = []
    
    # 1. Questionnaire Instrument Validation (FR-03)
    if instrument_validation and instrument_validation.get("is_applicable"):
        val_data = instrument_validation
        alpha_val = val_data["reliability"]["cronbach_alpha"]
        is_rel = val_data["reliability"]["is_reliable"]
        rel_status = "Reliabel" if is_rel else "Tidak Reliabel"
        
        inst_desc = (
            f"### **Uji Validitas & Reliabilitas Instrumen**\n\n"
            f"Pengujian keandalan instrumen penelitian (kuesioner) dilakukan menggunakan Uji Reliabilitas Cronbach's Alpha. "
            f"Diperoleh nilai koefisien Alpha sebesar **{alpha_val:.4f}** (ambang batas = {val_data['reliability']['threshold']}). "
            f"Dengan demikian, instrumen dinyatakan **{rel_status}** untuk digunakan dalam penelitian.\n\n"
            f"Untuk pengujian keabsahan tiap item instrumen, dilakukan Uji Validitas (Corrected Item-Total Correlation) "
            f"dengan hasil sebagai berikut:\n"
        )
        
        items_dict = val_data["validity"]["items"]
        for item, res in items_dict.items():
            valid_status = "Valid" if res["is_valid"] else "Tidak Valid (Gugur)"
            inst_desc += (
                f"- Item **{item}**: Nilai korelasi item-total r = **{res['correlation_coefficient']:.4f}** (p-value = {res['p_value']:.4f}), "
                f"dinyatakan **{valid_status}**.\n"
            )
            
        narrative_parts.append(inst_desc)

    # 2. Descriptive Analysis Summary (FR-06b)
    if descriptive_stats:
        desc_desc = "### **Analisis Deskriptif Data**\n\nRingkasan statistik deskriptif untuk variabel utama adalah sebagai berikut:\n"
        for col, stats_data in descriptive_stats.items():
            desc_desc += (
                f"- Variabel **{col}** ($N = {stats_data['count']}$): Rata-rata (Mean) = **{stats_data['mean']:.4f}**, "
                f"Median = **{stats_data['median']:.4f}**, Modus = **{stats_data['mode']:.4f}**, "
                f"Standar Deviasi = **{stats_data['std']:.4f}**, serta rentang nilai antara **{stats_data['min']:.4f}** hingga **{stats_data['max']:.4f}**.\n"
            )
        narrative_parts.append(desc_desc)

    # 3. Time Series Decision Engine Narrative (FR-05)
    if time_series_results:
        ts = time_series_results
        d = ts["differencing_degree"]
        stat_log = ts["stationarity_log"]
        
        ts_desc = (
            f"### **Analisis Deret Waktu (Time-Series)**\n\n"
            f"Data diidentifikasi memiliki struktur deret waktu (Time-Series). Sistem menjalankan uji stasioneritas "
            f"menggunakan metode **ADF (Augmented Dickey-Fuller)** dan **KPSS** pada variabel dependen '{dependent_var}'.\n\n"
        )
        
        for log in stat_log:
            diff_lbl = "Data Asli" if log["differencing_degree"] == 0 else f"Differencing Tingkat-{log['differencing_degree']}"
            stat_lbl = "Stasioner" if log["is_stationary"] else "Tidak Stasioner (Memiliki Unit Root)"
            ts_desc += (
                f"- **{diff_lbl}**: ADF p-value = **{log['adf_p_value']:.4f}**, KPSS p-value = **{log['kpss_p_value']:.4f}** "
                f"-> Dinyatakan **{stat_lbl}**.\n"
            )
            
        final_status = "Stasioner" if ts["is_stationary_final"] else "Tidak Stasioner"
        ts_desc += f"\nPada akhirnya, data diproses pada tingkat differencing $d = {d}$ (**{final_status}**) dan dimodelkan menggunakan model **{ts['model_type']}**.\n\n"
        
        # Details of fit
        details = ts["model_details"]
        if ts["model_type"] == "ARIMA":
            ts_desc += (
                f"Model ARIMA terpilih adalah ARIMA**{details['order']}** dengan nilai informasi AIC = **{details['aic']:.2f}** "
                f"dan BIC = **{details['bic']:.2f}**.\n\n"
                f"**Nilai Parameter Koefisien Model ARIMA:**\n"
            )
            for name, coef in details["coefficients"].items():
                p_val = details["p_values"].get(name, 1.0)
                sig_txt = "Signifikan" if p_val < alpha else "Tidak Signifikan"
                ts_desc += f"- Parameter **{name}**: Koefisien = **{coef:.4f}** (p-value = {p_val:.4f}) -> **{sig_txt}**.\n"
        else:
            ts_desc += (
                f"Model VAR yang dilatih menggunakan lag order = **{details['lags_selected']}** dengan nilai AIC = **{details['aic']:.2f}** "
                f"dan BIC = **{details['bic']:.2f}**.\n"
            )
            
        # Predictions
        forecasts_str = ", ".join([f"{f:.4f}" for f in ts["forecasts_5_steps"]])
        ts_desc += f"\n**Prediksi/Peramalan 5 Periode ke Depan:**\nNilai estimasi untuk 5 langkah berikutnya adalah: **[{forecasts_str}]**."
        
        narrative_parts.append(ts_desc)
        return "\n\n".join(narrative_parts)

    # 4. Normality & Routing Narrative (FR-06)
    norm_test = normality_results["test_name"]
    norm_p = normality_results["p_value"]
    is_normal = normality_results["is_normal"]
    model_type = analysis_results["model_type"]
    
    norm_desc = (
        f"### **Pengecekan Asumsi Normalitas & Routing Uji**\n\n"
        f"Uji normalitas dilakukan pada variabel dependen '{dependent_var}' menggunakan metode **{norm_test}** "
        f"sebagai gatekeeper penentuan uji parametrik vs non-parametrik. Diperoleh nilai signifikansi p-value sebesar **{norm_p:.4f}**.\n\n"
    )
    if is_normal:
        norm_desc += (
            f"Karena p-value $\ge {alpha:.2f}$, data dinyatakan **berdistribusi normal**. "
            f"Oleh karena itu, sistem mengarahkan analisis ke metode **Parametrik**, yaitu **{model_type}**."
        )
    else:
        norm_desc += (
            f"Karena p-value < {alpha:.2f}, data dinyatakan **tidak berdistribusi normal**. "
            f"Oleh karena itu, sistem dialihkan secara otomatis ke metode **Non-Parametrik**, yaitu **{model_type}**."
        )
    narrative_parts.append(norm_desc)

    # 5. Main Inferential Test Narrative
    test_desc = f"### **Hasil Pengujian Hipotesis ({model_type})**\n\n"
    
    if "Regression" in model_type:
        metrics = analysis_results["metrics"]
        r2 = metrics["r_squared"]
        r2_pct = r2 * 100
        f_p = metrics["p_value"]
        coefs = analysis_results["coefficients"]
        
        # Multicollinearity check
        if analysis_results.get("vif_eliminations"):
            test_desc += "**Uji Asumsi Multikolinearitas (VIF):**\n"
            for elim in analysis_results["vif_eliminations"]:
                test_desc += f"- {elim}\n"
            test_desc += "\n"
            
        # Simultan
        if f_p < alpha:
            test_desc += (
                f"Secara **simultan (F-Test)**, model regresi ini dinyatakan **signifikan** (p-value = **{f_p:.4f}** < {alpha}). "
                f"Kombinasi variabel independen ({', '.join(analysis_results['final_predictors'])}) berpengaruh secara nyata terhadap variabel dependen '{dependent_var}'. "
                f"Model memiliki nilai Koefisien Determinasi ($R^2 = {r2:.4f}$), yang menunjukkan bahwa variasi variabel independen "
                f"mampu menjelaskan perubahan pada '{dependent_var}' sebesar **{r2_pct:.1f}%**, sedangkan sisanya sebesar {100-r2_pct:.1f}% "
                f"dijelaskan oleh faktor lain di luar model.\n\n"
            )
        else:
            test_desc += (
                f"Secara **simultan**, model regresi dinyatakan **tidak signifikan** (p-value = **{f_p:.4f}** $\ge {alpha}$). "
                f"Artinya, tidak terdapat pengaruh yang nyata secara bersama-sama dari variabel independen "
                f"terhadap variabel dependen '{dependent_var}'.\n\n"
            )
            
        # Parsial
        test_desc += "Secara **parsial (t-Test)**, pengaruh masing-masing variabel independen adalah:\n"
        for var in analysis_results["final_predictors"]:
            if var in coefs:
                c_info = coefs[var]
                coef = c_info["coefficient"]
                p_val = c_info["p_value"]
                direction = "positif" if coef > 0 else "negatif"
                sig_text = "signifikan" if p_val < alpha else "tidak signifikan"
                
                test_desc += (
                    f"- Variabel **{var}**: Berpengaruh {direction} dan **{sig_text}** terhadap '{dependent_var}' "
                    f"(koefisien arah $\\beta$ = **{coef:.4f}**, p-value = {p_val:.4f}). "
                )
                
                if p_val < alpha:
                    test_desc += (
                        f"Setiap peningkatan satu satuan pada '{var}' akan meningkatkan "
                        if coef > 0 else 
                        f"Setiap peningkatan satu satuan pada '{var}' akan menurunkan "
                    )
                    test_desc += f"'{dependent_var}' sebesar **{abs(coef):.4f}** satuan, dengan asumsi variabel lain konstan.\n"
                else:
                    test_desc += "Variasi variabel ini tidak terbukti nyata mempengaruhi variabel dependen.\n"

    elif "Correlation" in model_type:
        results = analysis_results["results"]
        test_desc += "Hasil uji korelasi bivariat menunjukkan hubungan berikut:\n"
        
        for var, res in results.items():
            coeff = res["correlation_coefficient"]
            p_val = res["p_value"]
            strength = res["strength"]
            direction = res["direction"]
            is_sig = res["is_significant"]
            
            sig_text = "signifikan" if is_sig else "tidak signifikan"
            dir_text = "searah (positif)" if direction == "positif" else "berlawanan arah (negatif)"
            coeff_sym = "r" if "Pearson" in model_type else "\\rho"
            
            detail = (
                f"- Hubungan antara **{var}** dengan **{dependent_var}**: Bernilai **{sig_text}** (p-value = **{p_val:.4f}**). "
                f"Kekuatan korelasi tergolong **{strength}** dengan koefisien korelasi (${coeff_sym} = {coeff:.4f}$) "
                f"dan arah hubungan yang {dir_text}. "
            )
            
            if is_sig:
                if coeff > 0:
                    detail += f"Semakin tinggi nilai '{var}', maka nilai '{dependent_var}' cenderung semakin meningkat.\n"
                else:
                    detail += f"Semakin tinggi nilai '{var}', maka nilai '{dependent_var}' cenderung semakin menurun.\n"
            else:
                detail += f"Tidak terdapat hubungan yang cukup kuat secara statistik antara '{var}' dan '{dependent_var}'.\n"
                
            test_desc += detail

    elif model_type in ["Independent Samples T-Test", "Mann-Whitney U Test", "Paired Samples T-Test", "Wilcoxon Signed-Rank Test"]:
        metrics = analysis_results["metrics"]
        p_val = metrics["p_value"]
        is_sig = metrics["is_significant"]
        groups = analysis_results["groups"]
        effect_name = metrics["effect_size_name"]
        effect_val = metrics["effect_size"]
        
        g1 = groups["group1"]
        g2 = groups["group2"]
        
        test_desc += f"Pengujian komparasi 2 kelompok menggunakan **{model_type}** menghasilkan p-value sebesar **{p_val:.4f}**.\n\n"
        
        center_metric = "Mean" if "T-Test" in model_type else "Median"
        g1_val = g1["mean"] if "T-Test" in model_type else g1["median"]
        g2_val = g2["mean"] if "T-Test" in model_type else g2["median"]
        
        if is_sig:
            test_desc += f"Karena p-value < {alpha}, maka **Hipotesis (H1) Diterima** (perbedaan signifikan secara statistik).\n"
            if g1_val > g2_val:
                test_desc += (
                    f"Nilai pusat ({center_metric}) kelompok **{g1['label']}** ({g1_val:.4f}) secara signifikan lebih tinggi "
                    f"dibandingkan kelompok **{g2['label']}** ({g2_val:.4f}). "
                )
            else:
                test_desc += (
                    f"Nilai pusat ({center_metric}) kelompok **{g2['label']}** ({g2_val:.4f}) secara signifikan lebih tinggi "
                    f"dibandingkan kelompok **{g1['label']}** ({g1_val:.4f}). "
                )
            test_desc += f"Kekuatan efek perbedaan ({effect_name}) terhitung sebesar **{effect_val:.4f}**.\n"
        else:
            test_desc += (
                f"Karena p-value $\ge {alpha}$, maka **Hipotesis Nol (H0) Diterima** (tidak ada perbedaan signifikan).\n"
                f"Secara statistik, kelompok **{g1['label']}** ({center_metric} = {g1_val:.4f}) dan kelompok "
                f"**{g2['label']}** ({center_metric} = {g2_val:.4f}) dianggap setara atau tidak berbeda nyata.\n"
            )

    elif model_type in ["One-Way ANOVA", "Kruskal-Wallis Test"]:
        metrics = analysis_results["metrics"]
        p_val = metrics["p_value"]
        is_sig = metrics["is_significant"]
        effect_name = metrics["effect_size_name"]
        effect_val = metrics["effect_size"]
        posthoc = analysis_results.get("post_hoc_results", [])
        
        test_desc += f"Pengujian komparasi multi-kelompok (> 2) menggunakan **{model_type}** menghasilkan p-value sebesar **{p_val:.4f}**.\n\n"
        
        if is_sig:
            test_desc += (
                f"Karena p-value < {alpha}, maka **Hipotesis (H1) Diterima**. Terdapat minimal satu pasang kelompok yang memiliki "
                f"perbedaan nilai yang signifikan. Besaran kekuatan efek perbedaan ({effect_name}) adalah **{effect_val:.4f}**.\n\n"
            )
            
            if posthoc:
                test_desc += "**Hasil Uji Perbandingan Berganda (Post-Hoc):**\n"
                for row in posthoc:
                    sig_lbl = "Signifikan" if row["is_significant"] else "Tidak Signifikan"
                    diff_dir = "lebih tinggi" if row["mean_diff"] > 0 else "lebih rendah"
                    test_desc += (
                        f"- Kelompok **{row['group1']}** dibanding **{row['group2']}**: "
                        f"Selisih = **{row['mean_diff']:.4f}** (p-value terkoreksi = {row['p_value_corrected']:.4f}) -> Dinyatakan **{sig_lbl}** "
                        f"(kelompok '{row['group1']}' {diff_dir} dibanding '{row['group2']}').\n"
                    )
            else:
                test_desc += "Namun, uji post-hoc tidak menghasilkan perbedaan pasangan grup yang signifikan secara individual.\n"
        else:
            test_desc += (
                f"Karena p-value $\ge {alpha}$, maka **Hipotesis Nol (H0) Diterima**. "
                f"Tidak ditemukan bukti empiris bahwa kelompok-kelompok data yang dibandingkan memiliki perbedaan nilai yang signifikan.\n"
            )

    elif "Path Analysis" in model_type:
        paths = analysis_results["paths"]
        sobel = analysis_results["sobel_test"]
        x_var = analysis_results["independent_var"]
        m_var = analysis_results["mediator_var"]
        
        test_desc += (
            f"Analisis mediasi sederhana (Path Analysis) dilakukan untuk menguji pengaruh **{x_var}** (X) terhadap **{dependent_var}** (Y) "
            f"melalui variabel mediator **{m_var}** (M) menggunakan **Sobel Test**.\n\n"
            f"**Koefisien Jalur Analisis Jalur:**\n"
            f"- **Jalur a** (X \u2192 M): Koefisien = **{paths['path_a']['coefficient']:.4f}** (p-value = {paths['path_a']['p_value']:.4f}). "
            f"Berpengaruh **{'signifikan' if paths['path_a']['is_significant'] else 'tidak signifikan'}**.\n"
            f"- **Jalur b** (M \u2192 Y, mengontrol X): Koefisien = **{paths['path_b']['coefficient']:.4f}** (p-value = {paths['path_b']['p_value']:.4f}). "
            f"Berpengaruh **{'signifikan' if paths['path_b']['is_significant'] else 'tidak signifikan'}**.\n"
            f"- **Jalur c'** (Direct Effect X \u2192 Y): Koefisien = **{paths['path_c_prime']['coefficient']:.4f}** (p-value = {paths['path_c_prime']['p_value']:.4f}). "
            f"Pengaruh langsung dinyatakan **{'signifikan' if paths['path_c_prime']['is_significant'] else 'tidak signifikan'}**.\n"
            f"- **Jalur c** (Total Effect X \u2192 Y): Koefisien = **{paths['path_c']['coefficient']:.4f}** (p-value = {paths['path_c']['p_value']:.4f}). "
            f"Pengaruh total dinyatakan **{'signifikan' if paths['path_c']['is_significant'] else 'tidak signifikan'}**.\n\n"
            f"**Hasil Sobel Test (Indirect Effect):**\n"
            f"- Besaran Efek Tidak Langsung (Indirect Effect) = **{sobel['indirect_effect']:.4f}**.\n"
            f"- Nilai Z-statistic Sobel = **{sobel['statistic_z']:.4f}** (p-value = **{sobel['p_value']:.4f}**).\n"
        )
        
        if sobel["is_significant"]:
            test_desc += (
                f"Karena p-value Sobel < {alpha}, efek mediasi dinyatakan **signifikan**. "
                f"Artinya, variabel '{m_var}' secara signifikan memediasi hubungan antara '{x_var}' dengan '{dependent_var}'."
            )
            if not paths['path_c_prime']['is_significant']:
                test_desc += " Tipe mediasi yang terjadi adalah **Mediasi Sempurna (Full Mediation)** karena pengaruh langsung (c') menjadi tidak signifikan setelah M dimasukkan."
            else:
                test_desc += " Tipe mediasi yang terjadi adalah **Mediasi Sebagian (Partial Mediation)** karena pengaruh langsung (c') tetap signifikan setelah M dimasukkan."
        else:
            test_desc += f"Karena p-value Sobel $\ge {alpha}$, efek mediasi dinyatakan **tidak signifikan**. Variabel '{m_var}' tidak terbukti memediasi hubungan secara nyata."

    narrative_parts.append(test_desc)

    # 6. Final Conclusion
    conclusion = "### **Kesimpulan Akhir Penelitian**\n\n"
    is_sig = False
    if "metrics" in analysis_results and "is_significant" in analysis_results["metrics"]:
        is_sig = analysis_results["metrics"]["is_significant"]
    elif "metrics" in analysis_results and "is_model_significant" in analysis_results["metrics"]:
        is_sig = analysis_results["metrics"]["is_model_significant"]
    elif "sobel_test" in analysis_results:
        is_sig = analysis_results["sobel_test"]["is_significant"]
        
    if is_sig:
        conclusion += (
            f"Berdasarkan seluruh rangkaian analisis di atas, diperoleh bukti statistik yang cukup kuat untuk **Menerima Hipotesis (H1)**. "
            f"Terdapat perbedaan/hubungan/pengaruh yang signifikan pada variabel-variabel penelitian yang diuji pada tingkat kepercayaan 95%."
        )
    else:
        conclusion += (
            f"Berdasarkan hasil analisis, diperoleh kesimpulan untuk **Menerima Hipotesis Nol (H0)**. "
            f"Tidak terdapat cukup bukti statistik untuk menyatakan adanya hubungan/pengaruh/perbedaan nyata pada variabel penelitian yang diuji."
        )
        
    narrative_parts.append(conclusion)
    
    return "\n\n".join(narrative_parts)
