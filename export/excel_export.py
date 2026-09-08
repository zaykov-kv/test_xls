import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
import io
from datetime import datetime
from core.charlson import CHARLSON_MAPPINGS
from core.elixhauser import ELIXHAUSER_MAPPINGS


def export_to_excel(df, filename="comorbidity_results.xlsx"):
    """
    Экспортирует результаты в Excel с форматированием.
    
    Args:
        df: DataFrame с результатами
        filename: Имя файла для сохранения
    
    Returns:
        bytes: Excel-файл в виде байтов
    """
    
    # Создаём Excel-файл
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # --- 1. Лист с результатами ---
        df.to_excel(writer, sheet_name='Results', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Results']
        
        # --- Стили ---
        # Шрифты
        header_font = Font(bold=True, color='FFFFFF', size=11)
        bold_font = Font(bold=True)
        final_font = Font(bold=True, color='0000FF')
        
        # Заливка
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        risk_fills = {
            '🟢 Низкий': PatternFill(start_color='92D050', end_color='92D050', fill_type='solid'),
            '🟡 Средний': PatternFill(start_color='FFC000', end_color='FFC000', fill_type='solid'),
            '🟠 Высокий': PatternFill(start_color='FF8C00', end_color='FF8C00', fill_type='solid'),
            '🔴 Очень высокий': PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
        }
        
        # Границы
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Выравнивание
        center_alignment = Alignment(horizontal='center', vertical='center')
        
        # --- Форматируем заголовки ---
        for col_num, column in enumerate(df.columns, 1):
            cell = worksheet.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
            cell.border = thin_border
        
        # --- Форматируем итоговые колонки ---
        final_columns = [
            'Original Charlson', 
            'Updated Charlson',
            'Charlson Risk',
            'AHRQ Elixhauser', 
            'van Walraven Elixhauser',
            'Elixhauser Risk'
        ]
        
        for row in range(2, len(df) + 2):  # +1 для заголовка
            for col_idx, col_name in enumerate(df.columns, 1):
                cell = worksheet.cell(row=row, column=col_idx)
                cell.border = thin_border
                cell.alignment = center_alignment
                
                # Выделяем итоговые колонки
                if col_name in final_columns:
                    if col_name in ['Charlson Risk', 'Elixhauser Risk']:
                        # Для зон риска используем цветовую индикацию
                        value = cell.value
                        if value in risk_fills:
                            cell.fill = risk_fills[value]
                        cell.font = bold_font
                    else:
                        # Для числовых итоговых колонок
                        cell.font = final_font
                        cell.fill = PatternFill(start_color='E6F3FF', end_color='E6F3FF', fill_type='solid')
        
        # --- Автоматическая ширина колонок ---
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 40)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # --- 2. Лист со статистикой ---
        stats_df = pd.DataFrame({
            'Показатель': [
                'Всего пациентов',
                'Средний Charlson (обн.)',
                'Медиана Charlson (обн.)',
                'Мин. Charlson (обн.)',
                'Макс. Charlson (обн.)',
                'Средний Elixhauser (vW)',
                'Медиана Elixhauser (vW)',
                'Мин. Elixhauser (vW)',
                'Макс. Elixhauser (vW)'
            ],
            'Значение': [
                len(df),
                df['Updated Charlson'].mean(),
                df['Updated Charlson'].median(),
                df['Updated Charlson'].min(),
                df['Updated Charlson'].max(),
                df['van Walraven Elixhauser'].mean(),
                df['van Walraven Elixhauser'].median(),
                df['van Walraven Elixhauser'].min(),
                df['van Walraven Elixhauser'].max()
            ]
        })
        
        stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        stats_worksheet = writer.sheets['Statistics']
        
        # Форматируем статистику
        for col_num, column in enumerate(stats_df.columns, 1):
            cell = stats_worksheet.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
        
        # Ширина колонок в статистике
        stats_worksheet.column_dimensions['A'].width = 30
        stats_worksheet.column_dimensions['B'].width = 20
        
        # --- 3. Лист с распределением по рискам ---
        risk_dist = pd.DataFrame({
            'Зона риска': ['Низкий', 'Средний', 'Высокий', 'Очень высокий'],
            'Charlson': [
                (df['Charlson Risk'] == '🟢 Низкий').sum(),
                (df['Charlson Risk'] == '🟡 Средний').sum(),
                (df['Charlson Risk'] == '🟠 Высокий').sum(),
                (df['Charlson Risk'] == '🔴 Очень высокий').sum()
            ],
            'Elixhauser': [
                (df['Elixhauser Risk'] == '🟢 Низкий').sum(),
                (df['Elixhauser Risk'] == '🟡 Средний').sum(),
                (df['Elixhauser Risk'] == '🟠 Высокий').sum(),
                (df['Elixhauser Risk'] == '🔴 Очень высокий').sum()
            ]
        })
        
        risk_dist.to_excel(writer, sheet_name='Risk Distribution', index=False)
        risk_worksheet = writer.sheets['Risk Distribution']
        
        # Форматируем распределение
        for col_num, column in enumerate(risk_dist.columns, 1):
            cell = risk_worksheet.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
        
        risk_worksheet.column_dimensions['A'].width = 20
        risk_worksheet.column_dimensions['B'].width = 20
        risk_worksheet.column_dimensions['C'].width = 20
        
        # --- 4. Лист с топ-заболеваниями ---
        charlson_cols = [col for col in CHARLSON_MAPPINGS.keys() if col in df.columns]
        freq = df[charlson_cols].sum().sort_values(ascending=False).head(10)
        
        top_df = pd.DataFrame({
            'Заболевание': freq.index,
            'Количество пациентов': freq.values,
            'Процент': (freq.values / len(df) * 100).round(1)
        })
        
        top_df.to_excel(writer, sheet_name='Top Diseases', index=False)
        top_worksheet = writer.sheets['Top Diseases']
        
        # Форматируем топ
        for col_num, column in enumerate(top_df.columns, 1):
            cell = top_worksheet.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment
        
        top_worksheet.column_dimensions['A'].width = 40
        top_worksheet.column_dimensions['B'].width = 25
        top_worksheet.column_dimensions['C'].width = 20
        
        # --- 5. Информационный лист ---
        info_worksheet = workbook.create_sheet('Info')
        info_worksheet['A1'] = 'Отчёт по индексам коморбидности'
        info_worksheet['A1'].font = Font(bold=True, size=14)
        info_worksheet['A3'] = f'Дата генерации: {datetime.now().strftime("%d.%m.%Y %H:%M")}'
        info_worksheet['A4'] = f'Всего пациентов: {len(df)}'
        info_worksheet['A5'] = f'Колонок Charlson: {len(CHARLSON_MAPPINGS)}'
        info_worksheet['A6'] = f'Колонок Elixhauser: {len(ELIXHAUSER_MAPPINGS)}'
        info_worksheet['A8'] = 'Индексы:'
        info_worksheet['A9'] = '1. Original Charlson (Charlson et al. 1987)'
        info_worksheet['A10'] = '2. Updated Charlson (Quan et al. 2011)'
        info_worksheet['A11'] = '3. AHRQ Elixhauser (Moore et al. 2017)'
        info_worksheet['A12'] = '4. van Walraven Elixhauser (van Walraven et al. 2009)'
        
        info_worksheet.column_dimensions['A'].width = 50
    
    return output.getvalue()