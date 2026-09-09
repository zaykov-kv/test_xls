"""
Модуль для загрузки и обработки файлов.
"""

import streamlit as st
import pandas as pd
from typing import Tuple, Dict, List, Optional


def get_upload_settings() -> Dict:
    """
    Отображает настройки загрузки и возвращает их.
    Использует session_state для отслеживания типа файла.
    """
    # Инициализация состояния
    if 'file_type_state' not in st.session_state:
        st.session_state.file_type_state = "Excel (.xlsx, .xls)"
    
    st.markdown("**⚙️ Настройки загрузки**")
    st.caption("💡 Настройте параметры, затем выберите файлы и нажмите 'Загрузить'")
    
    col1, col2 = st.columns(2)
    
    with col1:
        file_type = st.selectbox(
            "Тип файла:",
            options=["Excel (.xlsx, .xls)", "CSV (.csv)"],
            index=0,
            help="Выберите формат загружаемого файла",
            key="file_type_select"
        )
        st.session_state.file_type_state = file_type
    
    with col2:
        if file_type == "CSV (.csv)":
            encoding = st.selectbox(
                "Кодировка:",
                options=["utf-8", "cp1251", "latin1", "iso-8859-1"],
                index=0,
                help="Выберите кодировку CSV-файла"
            )
        else:
            encoding = "utf-8"
            st.info("💡 Кодировка применяется только для CSV-файлов")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sheet_name = st.number_input(
            "Номер листа (Excel):",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
            help="Номер листа в Excel-файле (1 = первый лист)",
            disabled=(file_type == "CSV (.csv)")
        )
    
    with col2:
        id_col = st.number_input(
            "Колонка ID:",
            min_value=1,
            max_value=26,
            value=1,
            step=1,
            help="Номер колонки с ID пациента (1 = колонка A)"
        )
    
    with col3:
        icd_col = st.number_input(
            "Колонка ICD-10:",
            min_value=1,
            max_value=26,
            value=2,
            step=1,
            help="Номер колонки с кодами МКБ-10 (2 = колонка B)"
        )
    
    with col4:
        start_row = st.number_input(
            "Начать со строки:",
            min_value=1,
            max_value=100,
            value=2,
            step=1,
            help="Строка, с которой начинаются данные (1 = первая строка)"
        )
    
    return {
        "file_type": file_type,
        "encoding": encoding,
        "sheet_name": sheet_name,
        "id_col": id_col,
        "icd_col": icd_col,
        "start_row": start_row
    }


def load_and_process_files(
    uploaded_files: List,
    settings: Dict
) -> Tuple[Dict, List]:
    """
    Загружает и обрабатывает файлы с заданными настройками.
    
    Args:
        uploaded_files: Список загруженных файлов
        settings: Словарь с настройками загрузки
    
    Returns:
        Tuple[Dict, List]: (all_results, combined_results)
    """
    all_results = {}
    combined_results = []
    
    total_files = len(uploaded_files)
    progress_bar = st.progress(0)
    
    for file_idx, uploaded_file in enumerate(uploaded_files):
        try:
            # Чтение файла в зависимости от типа
            if settings["file_type"] == "CSV (.csv)":
                df = pd.read_csv(
                    uploaded_file,
                    encoding=settings["encoding"],
                    skiprows=settings["start_row"] - 1,
                    header=None
                )
            else:
                df = pd.read_excel(
                    uploaded_file,
                    sheet_name=settings["sheet_name"] - 1,
                    skiprows=settings["start_row"] - 1,
                    engine='openpyxl',
                    header=None
                )
            
            # Проверяем, что есть данные
            if df.empty:
                st.warning(f"⚠️ Файл '{uploaded_file.name}' пуст, пропускаем")
                continue
            
            # Проверяем количество колонок
            max_col = max(settings["id_col"], settings["icd_col"])
            if len(df.columns) < max_col:
                st.warning(f"⚠️ В файле '{uploaded_file.name}' меньше {max_col} колонок, пропускаем")
                continue
            
            # Извлекаем нужные колонки
            df = df.iloc[:, [settings["id_col"] - 1, settings["icd_col"] - 1]]
            df.columns = ['Patient_ID', 'ICD_codes']
            
            # Преобразуем в строки
            df['Patient_ID'] = df['Patient_ID'].astype(str)
            df['ICD_codes'] = df['ICD_codes'].astype(str)
            
            # Удаляем пустые строки
            df = df[df['Patient_ID'].str.strip() != '']
            df = df[df['ICD_codes'].str.strip() != '']
            
            if df.empty:
                st.warning(f"⚠️ В файле '{uploaded_file.name}' нет данных после обработки, пропускаем")
                continue
            
            # Расчёт для каждого пациента
            from processing.analysis import calculate_patients
            from core.utils import add_risk_zones
            
            results = calculate_patients(df, uploaded_file.name)
            result_df = pd.DataFrame(results)
            result_df = add_risk_zones(result_df)
            
            all_results[uploaded_file.name] = result_df
            combined_results.append(result_df)
            
            progress_bar.progress((file_idx + 1) / total_files)
            
        except Exception as e:
            st.error(f"❌ Ошибка при обработке файла '{uploaded_file.name}': {str(e)}")
            continue
    
    progress_bar.empty()
    
    return all_results, combined_results


def render_upload_section() -> Optional[Tuple[Dict, List]]:
    """
    Отображает интерфейс загрузки и обрабатывает файлы.
    
    Returns:
        Optional[Tuple[Dict, List]]: (all_results, combined_results) или None
    """
    # --- ФОРМА ДЛЯ НАСТРОЕК И ЗАГРУЗКИ ---
    with st.form(key="upload_form"):
        settings = get_upload_settings()
        
        st.markdown("---")
        st.markdown("**📁 Выберите файлы для загрузки**")
        
        uploaded_files = st.file_uploader(
            "Загрузите один или несколько файлов",
            type=['xlsx', 'xls', 'csv'],
            accept_multiple_files=True,
            help="Файлы должны содержать минимум 2 колонки: ID пациента и коды МКБ-10",
            label_visibility="collapsed"
        )
        
        # Кнопка отправки формы
        submitted = st.form_submit_button(
            "📤 Загрузить и обработать",
            use_container_width=True,
            type="primary"
        )
    
    # --- ОБРАБОТКА ФАЙЛОВ ПОСЛЕ НАЖАТИЯ КНОПКИ ---
    if submitted and uploaded_files:
        with st.spinner("⏳ Обработка файлов..."):
            return load_and_process_files(uploaded_files, settings)
    
    elif submitted and not uploaded_files:
        st.warning("⚠️ Выберите хотя бы один файл для загрузки")
    
    return None