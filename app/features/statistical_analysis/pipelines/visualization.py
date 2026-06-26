import os
import io
import base64
import matplotlib
# Force matplotlib to run in headless mode
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Dict, Any, List
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.config import EXPORT_DIR

# Establish a consistent aesthetic theme
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Calibri']

def generate_plot(
    df: pd.DataFrame,
    model_type: str,
    independent_vars: List[str],
    dependent_var: str,
    group_var: str = None
) -> io.BytesIO:
    """
    Generates a statistical plot based on the model type.
    Returns a BytesIO buffer containing the PNG image.
    """
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)
    
    # Premium color palette
    primary_color = "#1E3A8A"  # Deep Blue
    secondary_color = "#0EA5E9"  # Sky Blue
    accent_color = "#F43F5E"  # Rose Red
    
    if model_type in ["Multiple Linear Regression", "Spearman Rank Correlation"]:
        # Plot primary independent variable vs dependent variable
        primary_x = independent_vars[0]
        
        # Draw scatter plot
        sns.scatterplot(
            data=df, 
            x=primary_x, 
            y=dependent_var, 
            color=primary_color, 
            alpha=0.7, 
            s=80, 
            edgecolor='w', 
            linewidth=0.5, 
            ax=ax
        )
        
        # Try to draw a trendline
        if len(df) > 1:
            try:
                sns.regplot(
                    data=df, 
                    x=primary_x, 
                    y=dependent_var, 
                    scatter=False, 
                    color=accent_color, 
                    line_kws={"linewidth": 2, "linestyle": "--"}, 
                    ax=ax
                )
            except Exception:
                pass
                
        ax.set_title(f"Hubungan antara {primary_x} dan {dependent_var}", fontsize=14, pad=15, fontweight='bold', color='#1F2937')
        ax.set_xlabel(primary_x, fontsize=11, fontweight='semibold', labelpad=10)
        ax.set_ylabel(dependent_var, fontsize=11, fontweight='semibold', labelpad=10)
        
    elif model_type in ["Independent Samples T-Test", "Mann-Whitney U Test"]:
        # Box plot for comparisons
        sns.boxplot(
            data=df, 
            x=group_var, 
            y=dependent_var, 
            palette=[secondary_color, primary_color],
            width=0.5, 
            linewidth=1.5,
            fliersize=5, 
            ax=ax
        )
        
        # Add swarm plot on top to show actual data points if dataset is not huge
        if len(df) < 150:
            sns.stripplot(
                data=df, 
                x=group_var, 
                y=dependent_var, 
                color="#111827", 
                size=5, 
                jitter=0.15, 
                alpha=0.5, 
                ax=ax
            )
            
        ax.set_title(f"Perbandingan {dependent_var} berdasarkan {group_var}", fontsize=14, pad=15, fontweight='bold', color='#1F2937')
        ax.set_xlabel(group_var, fontsize=11, fontweight='semibold', labelpad=10)
        ax.set_ylabel(dependent_var, fontsize=11, fontweight='semibold', labelpad=10)
        
    # Clean layout margins
    plt.tight_layout()
    
    # Save to BytesIO
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close(fig)
    return buf

def encode_image_base64(buf: io.BytesIO) -> str:
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def create_docx_report(
    file_id: str,
    filename: str,
    preprocessing_log: Dict[str, Any],
    normality_results: Dict[str, Any],
    analysis_results: Dict[str, Any],
    independent_vars: List[str],
    dependent_var: str,
    narrative: str,
    plot_buf: io.BytesIO,
    group_var: str = None
) -> str:
    """
    Generates a structured .docx report and saves it to the exports directory.
    Returns the absolute file path of the generated report.
    """
    doc = Document()
    
    # Page setup - Margins (1 inch)
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        
    # Custom styles
    # Colors
    c_primary = RGBColor(30, 58, 138)    # Deep Blue
    c_secondary = RGBColor(14, 165, 233) # Sky Blue
    c_text = RGBColor(31, 41, 55)        # Dark Charcoal
    
    # --- Title Section ---
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_p.add_run("LAPORAN ANALISIS STATISTIK OTOMATIS")
    title_run.font.name = 'Calibri'
    title_run.font.size = Pt(18)
    title_run.font.bold = True
    title_run.font.color.rgb = c_primary
    
    subtitle_p = doc.add_paragraph()
    subtitle_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle_p.add_run(f"Analisis pada file: {filename}\nDihasilkan oleh Sistem Olahin")
    subtitle_run.font.name = 'Calibri'
    subtitle_run.font.size = Pt(11)
    subtitle_run.font.italic = True
    subtitle_run.font.color.rgb = RGBColor(107, 114, 128)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    
    # Helper to add section headers
    def add_section_header(text: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = c_primary
        
    # --- SECTION 1: Ringkasan & Pembersihan Data ---
    add_section_header("1. Ringkasan & Pembersihan Data")
    
    p = doc.add_paragraph()
    p.add_run(
        f"Proses ingestion mendeteksi total baris data awal sebanyak {preprocessing_log['initial_rows']} baris. "
        f"Sistem preprocessing otomatis melakukan penyesuaian tipe data dan pembersihan nilai kosong serta outlier "
        f"pada kolom terpilih: "
    )
    p.add_run(f"Dependen: '{dependent_var}'").bold = True
    if independent_vars:
        p.add_run(", Independen: ")
        p.add_run(f"'{', '.join(independent_vars)}'").bold = True
    if group_var:
        p.add_run(", Variabel Grup: ")
        p.add_run(f"'{group_var}'").bold = True
        
    # Table of cleaning results
    table = doc.add_table(rows=3, cols=2)
    table.style = 'Light Shading Accent 1'
    
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Parameter Data'
    hdr_cells[1].text = 'Nilai / Keterangan'
    
    row_cells = table.rows[1].cells
    row_cells[0].text = 'Jumlah Baris Awal'
    row_cells[1].text = str(preprocessing_log['initial_rows'])
    
    row_cells = table.rows[2].cells
    row_cells[0].text = 'Jumlah Baris Setelah Pembersihan (Final)'
    row_cells[1].text = str(preprocessing_log['final_rows'])
    
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    
    # Log actions list
    if preprocessing_log["actions_taken"]:
        doc.add_paragraph().add_run("Tindakan pembersihan yang dilakukan secara otomatis:").bold = True
        for action in preprocessing_log["actions_taken"]:
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(3)
            p.add_run(action)
    else:
        doc.add_paragraph("Tidak ada pembersihan (data sudah bersih).")
        
    # --- SECTION 2: Hasil Uji Normalitas ---
    add_section_header("2. Hasil Uji Normalitas")
    
    norm_status = "Berdistribusi Normal" if normality_results["is_normal"] else "Tidak Berdistribusi Normal"
    
    table_norm = doc.add_table(rows=4, cols=2)
    table_norm.style = 'Light Shading Accent 1'
    
    table_norm.rows[0].cells[0].text = 'Uji Normalitas'
    table_norm.rows[0].cells[1].text = normality_results['test_name']
    
    table_norm.rows[1].cells[0].text = 'Nilai Statistik Uji'
    table_norm.rows[1].cells[1].text = f"{normality_results['statistic']:.4f}"
    
    table_norm.rows[2].cells[0].text = 'p-value'
    table_norm.rows[2].cells[1].text = f"{normality_results['p_value']:.4f}"
    
    table_norm.rows[3].cells[0].text = 'Kesimpulan Distribusi'
    table_norm.rows[3].cells[1].text = norm_status
    table_norm.rows[3].cells[1].paragraphs[0].runs[0].font.bold = True
    
    # --- SECTION 3: Hasil Analisis Statistik ---
    model_type = analysis_results["model_type"]
    add_section_header(f"3. Hasil Uji Hipotesis ({model_type})")
    
    if model_type == "Multiple Linear Regression":
        # Regression parameters table
        coefs = analysis_results["coefficients"]
        table_reg = doc.add_table(rows=len(coefs) + 1, cols=5)
        table_reg.style = 'Light Shading Accent 1'
        
        hdr = table_reg.rows[0].cells
        hdr[0].text = 'Variabel'
        hdr[1].text = 'Koefisien (\u03b2)'
        hdr[2].text = 'Std Error'
        hdr[3].text = 't-Statistik'
        hdr[4].text = 'p-value'
        
        for idx, (var, stats_data) in enumerate(coefs.items(), start=1):
            row = table_reg.rows[idx].cells
            row[0].text = "Konstanta" if var == 'const' else var
            row[1].text = f"{stats_data['coefficient']:.4f}"
            row[2].text = f"{stats_data['std_err']:.4f}"
            row[3].text = f"{stats_data['t_statistic']:.4f}"
            row[4].text = f"{stats_data['p_value']:.4f}"
            if stats_data['is_significant']:
                row[4].paragraphs[0].runs[0].font.bold = True
                
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        
        # Regression summary table
        metrics = analysis_results["metrics"]
        table_sum = doc.add_table(rows=3, cols=2)
        table_sum.style = 'Light Shading Accent 1'
        
        table_sum.rows[0].cells[0].text = 'R-Square ($R^2$)'
        table_sum.rows[0].cells[1].text = f"{metrics['r_squared']:.4f}"
        table_sum.rows[1].cells[0].text = 'F-Statistik'
        table_sum.rows[1].cells[1].text = f"{metrics['f_statistic']:.4f}"
        table_sum.rows[2].cells[0].text = 'Model p-value'
        table_sum.rows[2].cells[1].text = f"{metrics['p_value']:.4f}"
        if metrics['is_model_significant']:
            table_sum.rows[2].cells[1].paragraphs[0].runs[0].font.bold = True

    elif model_type == "Spearman Rank Correlation":
        # Spearman table
        res_dict = analysis_results["results"]
        table_spear = doc.add_table(rows=len(res_dict) + 1, cols=5)
        table_spear.style = 'Light Shading Accent 1'
        
        hdr = table_spear.rows[0].cells
        hdr[0].text = 'Variabel Independen'
        hdr[1].text = 'Koefisien Korelasi (\u03c1)'
        hdr[2].text = 'p-value'
        hdr[3].text = 'Kekuatan'
        hdr[4].text = 'Arah'
        
        for idx, (var, stats_data) in enumerate(res_dict.items(), start=1):
            row = table_spear.rows[idx].cells
            row[0].text = var
            row[1].text = f"{stats_data['correlation_coefficient']:.4f}"
            row[2].text = f"{stats_data['p_value']:.4f}"
            row[3].text = stats_data['strength']
            row[4].text = stats_data['direction']
            if stats_data['is_significant']:
                row[2].paragraphs[0].runs[0].font.bold = True

    elif model_type in ["Independent Samples T-Test", "Mann-Whitney U Test"]:
        groups = analysis_results["groups"]
        metrics = analysis_results["metrics"]
        g1 = groups["group1"]
        g2 = groups["group2"]
        
        metric_name = "Mean" if model_type == "Independent Samples T-Test" else "Median"
        g1_val = g1["mean"] if model_type == "Independent Samples T-Test" else g1["median"]
        g2_val = g2["mean"] if model_type == "Independent Samples T-Test" else g2["median"]
        
        # Group stats table
        table_groups = doc.add_table(rows=3, cols=4)
        table_groups.style = 'Light Shading Accent 1'
        
        hdr = table_groups.rows[0].cells
        hdr[0].text = 'Kelompok'
        hdr[1].text = 'Jumlah Sampel (N)'
        hdr[2].text = f'Nilai Pusat ({metric_name})'
        hdr[3].text = 'Keterangan'
        
        r1 = table_groups.rows[1].cells
        r1[0].text = str(g1["label"])
        r1[1].text = str(g1["count"])
        r1[2].text = f"{g1_val:.4f}"
        r1[3].text = "Kelompok 1"
        
        r2 = table_groups.rows[2].cells
        r2[0].text = str(g2["label"])
        r2[1].text = str(g2["count"])
        r2[2].text = f"{g2_val:.4f}"
        r2[3].text = "Kelompok 2"
        
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        
        # Test stats table
        table_comp_res = doc.add_table(rows=3, cols=2)
        table_comp_res.style = 'Light Shading Accent 1'
        
        stat_lbl = "t-Statistik" if model_type == "Independent Samples T-Test" else "U-Statistik"
        stat_val = metrics["t_statistic"] if model_type == "Independent Samples T-Test" else metrics["u_statistic"]
        
        table_comp_res.rows[0].cells[0].text = 'Metode Uji'
        table_comp_res.rows[0].cells[1].text = model_type
        
        table_comp_res.rows[1].cells[0].text = stat_lbl
        table_comp_res.rows[1].cells[1].text = f"{stat_val:.4f}"
        
        table_comp_res.rows[2].cells[0].text = 'p-value'
        table_comp_res.rows[2].cells[1].text = f"{metrics['p_value']:.4f}"
        if metrics['is_significant']:
            table_comp_res.rows[2].cells[1].paragraphs[0].runs[0].font.bold = True

    # --- SECTION 4: Interpretasi Naratif ---
    add_section_header("4. Interpretasi Hasil Analisis")
    
    # Split narrative by paragraphs and write to docx
    for paragraph in narrative.split("\n\n"):
        if paragraph.strip():
            # Support basic Markdown bold (**word**)
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            
            parts = paragraph.split("**")
            is_bold = False
            for part in parts:
                run = p.add_run(part)
                run.font.name = 'Calibri'
                run.font.size = Pt(11)
                run.font.color.rgb = c_text
                if is_bold:
                    run.bold = True
                is_bold = not is_bold
                
    # --- SECTION 5: Visualisasi Grafik ---
    add_section_header("5. Visualisasi Grafik")
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # Reset file pointer and add picture
    plot_buf.seek(0)
    p.add_run().add_picture(plot_buf, width=Inches(5.2))
    
    caption_p = doc.add_paragraph()
    caption_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_run = caption_p.add_run("Gambar 5.1 Grafik Hasil Analisis Statistik")
    caption_run.font.name = 'Calibri'
    caption_run.font.size = Pt(9.5)
    caption_run.font.italic = True
    caption_run.font.color.rgb = RGBColor(107, 114, 128)
    
    # Save Report
    report_filename = f"{file_id}_report.docx"
    report_path = os.path.join(EXPORT_DIR, report_filename)
    doc.save(report_path)
    
    return report_filename
