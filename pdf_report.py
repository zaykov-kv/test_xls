try:
    from fpdf import FPDF
except ImportError:
    try:
        from fpdf import FPDF
    except ImportError:
        raise ImportError("Установите fpdf2: pip install fpdf2")

import tempfile
import os
from datetime import datetime
import pandas as pd
from charlson import CHARLSON_MAPPINGS


def generate_pdf_report(df, filename="comorbidity_report.pdf"):
    """
    Генерирует PDF-отчёт с результатами анализа.
    """
    
    class PDF(FPDF):
        def __init__(self):
            super().__init__()
            # Используем стандартный шрифт, но заменяем все специальные символы
            self.use_font = 'helvetica'
        
        def header(self):
            self.set_font(self.use_font, 'B', 14)
            self.cell(0, 10, 'Otchet po indeksam komorbidnosti', 0, 1, 'C')
            self.set_font(self.use_font, '', 10)
            self.cell(0, 6, f'Data: {datetime.now().strftime("%d.%m.%Y %H:%M")}', 0, 1, 'C')
            self.ln(5)
        
        def footer(self):
            self.set_y(-15)
            self.set_font(self.use_font, 'I', 8)
            self.cell(0, 10, f'Stranitsa {self.page_no()}', 0, 0, 'C')
        
        def chapter_title(self, title):
            self.set_font(self.use_font, 'B', 12)
            self.cell(0, 10, title, 0, 1, 'L')
            self.ln(2)
        
        def chapter_body(self, text):
            self.set_font(self.use_font, '', 10)
            # Заменяем эмодзи на текстовые обозначения
            text = self.replace_emojis(text)
            self.multi_cell(0, 6, text)
            self.ln(4)
        
        def replace_emojis(self, text):
            """Заменяет эмодзи на текстовые обозначения"""
            replacements = {
                '🟢': '[Low]',
                '🟡': '[Medium]',
                '🟠': '[High]',
                '🔴': '[Very High]',
                '📊': '[Stats]',
                '📈': '[Chart]',
                '🏆': '[Top]',
                '🌡️': '[Heatmap]',
                '📋': '[Data]',
                '📥': '[Download]',
                'ℹ️': '[Info]',
                '💡': '[Note]',
                '✅': '[OK]',
                '❌': '[Error]',
                '⚠️': '[Warning]',
                '👆': '[Click]',
                '🏥': '[Hospital]',
                '🔍': '[Search]',
                '🎯': '[Target]'
            }
            for emoji, replacement in replacements.items():
                text = text.replace(emoji, replacement)
            return text
    
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- 1. General statistics ---
    pdf.chapter_title('1. Obshchaya statistika')
    
    # Заменяем эмодзи в данных
    stats_text = f"""
Vsego patsientov: {len(df)}
Diapazon ballov Charlson (obn.): {df['Updated Charlson'].min():.0f} - {df['Updated Charlson'].max():.0f}
Sredniy ball Charlson (obn.): {df['Updated Charlson'].mean():.2f}
Mediana Charlson (obn.): {df['Updated Charlson'].median():.2f}
Sredniy ball Elixhauser (vW): {df['van Walraven Elixhauser'].mean():.2f}
Mediana Elixhauser (vW): {df['van Walraven Elixhauser'].median():.2f}
    """
    pdf.chapter_body(stats_text)
    
    # --- 2. Risk zones (Charlson) ---
    pdf.chapter_title('2. Raspredelenie po zonam riska (Charlson)')
    
    risk_dist = df['Charlson Risk'].value_counts()
    # Маппинг для замены значений риска
    risk_map = {
        '🟢 Низкий': 'Low',
        '🟡 Средний': 'Medium',
        '🟠 Высокий': 'High',
        '🔴 Очень высокий': 'Very High'
    }
    
    risk_text = ""
    for orig_risk, display_risk in risk_map.items():
        if orig_risk in risk_dist.index:
            count = risk_dist[orig_risk]
            pct = (count / len(df)) * 100
            risk_text += f"{display_risk}: {count} ({pct:.1f}%)\n"
    pdf.chapter_body(risk_text)
    
    # --- 3. Risk zones (Elixhauser) ---
    pdf.chapter_title('3. Raspredelenie po zonam riska (Elixhauser)')
    
    risk_dist = df['Elixhauser Risk'].value_counts()
    risk_text = ""
    for orig_risk, display_risk in risk_map.items():
        if orig_risk in risk_dist.index:
            count = risk_dist[orig_risk]
            pct = (count / len(df)) * 100
            risk_text += f"{display_risk}: {count} ({pct:.1f}%)\n"
    pdf.chapter_body(risk_text)
    
    # --- 4. Top-10 diseases (Charlson) ---
    pdf.chapter_title('4. Top-10 zabolevaniy (Charlson)')
    
    charlson_cols = [col for col in CHARLSON_MAPPINGS.keys() if col in df.columns]
    freq = df[charlson_cols].sum().sort_values(ascending=False).head(10)
    
    top_text = ""
    for idx, (disease, count) in enumerate(freq.items(), 1):
        pct = (count / len(df)) * 100 if len(df) > 0 else 0
        top_text += f"{idx}. {disease}: {int(count)} ({pct:.1f}%)\n"
    pdf.chapter_body(top_text)
    
    # --- 5. Table with results (first 20 patients) ---
    pdf.add_page()
    pdf.chapter_title('5. Rezultaty po patsientam (pervye 20)')
    
    display_cols = ['Patient_ID', 'Updated Charlson', 'Charlson Risk', 
                    'van Walraven Elixhauser', 'Elixhauser Risk']
    display_cols = [col for col in display_cols if col in df.columns]
    
    pdf.set_font(pdf.use_font, 'B', 8)
    col_widths = [30, 30, 35, 35, 35]
    headers = ['ID', 'Charlson', 'Risk C', 'Elixhauser', 'Risk E']
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, 1, 0, 'C')
    pdf.ln()
    
    pdf.set_font(pdf.use_font, '', 7)
    for idx, row in df.head(20).iterrows():
        pdf.cell(col_widths[0], 6, str(row['Patient_ID'])[:10], 1, 0, 'C')
        pdf.cell(col_widths[1], 6, f"{row['Updated Charlson']:.0f}", 1, 0, 'C')
        
        # Конвертируем риск в английский
        risk_val = row['Charlson Risk']
        risk_en = risk_map.get(risk_val, risk_val)
        pdf.cell(col_widths[2], 6, risk_en, 1, 0, 'C')
        
        pdf.cell(col_widths[3], 6, f"{row['van Walraven Elixhauser']:.0f}", 1, 0, 'C')
        
        risk_val = row['Elixhauser Risk']
        risk_en = risk_map.get(risk_val, risk_val)
        pdf.cell(col_widths[4], 6, risk_en, 1, 0, 'C')
        pdf.ln()
    
    pdf.ln(4)
    pdf.set_font(pdf.use_font, 'I', 8)
    pdf.cell(0, 6, f'Pervye 20 iz {len(df)} patsientov. Polnye dannye dostupny v CSV.', 0, 1, 'C')
    
    # --- Сохранение ---
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        pdf.output(tmp_file.name)
        tmp_file_path = tmp_file.name
    
    with open(tmp_file_path, 'rb') as f:
        pdf_bytes = f.read()
    
    os.unlink(tmp_file_path)
    return pdf_bytes