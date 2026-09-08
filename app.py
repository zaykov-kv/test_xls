import streamlit as st
import pandas as pd
from datetime import datetime

# Импорты из модулей
from core import CHARLSON_MAPPINGS, ELIXHAUSER_MAPPINGS
from processing.data_processor import process_uploaded_files
from visualizations import (
    render_file_info,
    render_raw_data,
    render_sidebar_filters,
    render_results_table,
    render_summary_stats,
    render_interactive_charts,
    render_standard_charts,
    render_code_validation,
    render_database_interface,
    render_loaded_data
)
from export import export_to_excel, generate_pdf_report

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="Калькулятор коморбидности",
    page_icon="🏥",
    layout="wide"
)

# --- ТЁМНАЯ ТЕМА ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# Переключатель в боковой панели
with st.sidebar:
    theme_toggle = st.toggle(
        "🌙 Тёмная тема", 
        value=(st.session_state.theme == 'dark'),
        help="Переключить между светлой и тёмной темой"
    )
    
    if theme_toggle:
        st.session_state.theme = 'dark'
    else:
        st.session_state.theme = 'light'

# Применяем CSS для тёмной темы
if st.session_state.theme == 'dark':
    st.markdown("""
    <style>
        .stApp { background-color: #0e1117; color: #fafafa; }
        .st-emotion-cache-1r6slb0, .st-emotion-cache-1v0mbdj, .st-emotion-cache-16txtl3 {
            background-color: #1e1e2e !important;
            border-radius: 10px;
            padding: 10px;
        }
        h1, h2, h3, h4, h5, h6 { color: #fafafa !important; }
        p, li, label, .stMarkdown { color: #d4d4d4 !important; }
        .stMetric { background-color: #1e1e2e !important; border-radius: 10px; padding: 15px; }
        .stMetric label { color: #aaa !important; }
        .stMetric .stMetricValue { color: #fafafa !important; }
        .stDataFrame { background-color: #1e1e2e !important; }
        .stButton button { background-color: #2d2d44 !important; color: #fafafa !important; border: 1px solid #444 !important; }
        .stButton button:hover { background-color: #3d3d5c !important; border-color: #666 !important; }
        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            background-color: #1e1e2e !important; color: #fafafa !important; border-color: #444 !important;
        }
        .stSidebar { background-color: #16161f !important; }
        .stSidebar h1, .stSidebar h2, .stSidebar h3 { color: #fafafa !important; }
        .stTabs [data-baseweb="tab-list"] { background-color: #1e1e2e !important; }
        .stTabs [data-baseweb="tab"] { color: #aaa !important; }
        .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #fafafa !important; background-color: #2d2d44 !important; }
        .stExpander { background-color: #1e1e2e !important; border-radius: 10px !important; border-color: #333 !important; }
        .stExpander summary { color: #fafafa !important; }
        .stFileUploader { background-color: #1e1e2e !important; border-color: #444 !important; }
        .stAlert { background-color: #1e1e2e !important; border-color: #444 !important; }
        .js-plotly-plot .plotly .main-svg { background-color: #1e1e2e !important; }
        .js-plotly-plot .plotly .cartesianlayer { background-color: #1e1e2e !important; }
        ::-webkit-scrollbar { background-color: #1e1e2e; width: 8px; }
        ::-webkit-scrollbar-thumb { background-color: #444; border-radius: 4px; }
        .stSelectbox div[data-baseweb="select"] { background-color: #1e1e2e !important; color: #fafafa !important; }
        .stSlider { color: #fafafa !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .stApp { background-color: #ffffff; color: #262730; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Калькулятор индексов Charlson и Elixhauser")
st.markdown("---")


# =============================================================================
# ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ СЕССИИ
# =============================================================================

if 'all_results' not in st.session_state:
    st.session_state.all_results = {}
if 'combined_df' not in st.session_state:
    st.session_state.combined_df = None
if 'uploaded_files_processed' not in st.session_state:
    st.session_state.uploaded_files_processed = False
if 'data_source' not in st.session_state:
    st.session_state.data_source = None


# =============================================================================
# БАЗА ДАННЫХ (ВСЕГДА ДОСТУПНА)
# =============================================================================

render_database_interface()


# =============================================================================
# ПРОВЕРКА КОДОВ МКБ-10 (ВСЕГДА ДОСТУПНА)  ← ПЕРЕМЕЩЕНО СЮДА
# =============================================================================

st.markdown("---")
render_code_validation({})


# =============================================================================
# ЗАГРУЗКА ФАЙЛА
# =============================================================================

st.markdown("---")
st.subheader("📂 Загрузка новых данных")

uploaded_files = st.file_uploader(
    "Загрузите один или несколько Excel-файлов",
    type=['xlsx', 'xls'],
    accept_multiple_files=True,
    help="Файлы должны содержать минимум 2 колонки: ID пациента и коды МКБ-10"
)


# =============================================================================
# ОСНОВНАЯ ЛОГИКА
# =============================================================================

if uploaded_files:
    process_new_files = True
    
    if st.session_state.uploaded_files_processed:
        current_names = [f.name for f in uploaded_files]
        session_names = list(st.session_state.all_results.keys()) if st.session_state.all_results else []
        if current_names == session_names:
            process_new_files = False
    
    if process_new_files:
        with st.spinner("⏳ Обработка файлов..."):
            all_results, combined_results = process_uploaded_files(uploaded_files)
        
        if all_results:
            st.session_state.all_results = all_results
            st.session_state.combined_df = pd.concat(combined_results, ignore_index=True)
            st.session_state.uploaded_files_processed = True
            st.session_state.data_source = 'file'
            st.success(f"✅ Загружено {len(all_results)} файлов, всего пациентов: {len(st.session_state.combined_df)}")
            st.rerun()
        else:
            st.warning("⚠️ Нет файлов для обработки")
            st.stop()

# --- ПРОВЕРКА НАЛИЧИЯ ДАННЫХ ---
has_data = (
    st.session_state.combined_df is not None and 
    not st.session_state.combined_df.empty
)

if has_data:
    data_source = st.session_state.data_source
    
    # --- ПРИВОДИМ КОЛОНКИ К ЕДИНОМУ ФОРМАТУ ---
    if data_source == 'database':
        rename_map = {}
        df = st.session_state.combined_df
        
        if 'patient_id_text' in df.columns and 'Patient_ID' not in df.columns:
            rename_map['patient_id_text'] = 'Patient_ID'
        if 'source_file' in df.columns and 'Source_File' not in df.columns:
            rename_map['source_file'] = 'Source_File'
        if 'icd_codes' in df.columns and 'ICD_codes' not in df.columns:
            rename_map['icd_codes'] = 'ICD_codes'
        if 'charlson_risk' in df.columns and 'Charlson Risk' not in df.columns:
            rename_map['charlson_risk'] = 'Charlson Risk'
        if 'elixhauser_risk' in df.columns and 'Elixhauser Risk' not in df.columns:
            rename_map['elixhauser_risk'] = 'Elixhauser Risk'
        if 'updated_charlson' in df.columns and 'Updated Charlson' not in df.columns:
            rename_map['updated_charlson'] = 'Updated Charlson'
        if 'van_walraven_elixhauser' in df.columns and 'van Walraven Elixhauser' not in df.columns:
            rename_map['van_walraven_elixhauser'] = 'van Walraven Elixhauser'
        
        if rename_map:
            st.session_state.combined_df = df.rename(columns=rename_map)
            st.info(f"🔄 Переименовано {len(rename_map)} колонок из формата базы данных")
        
        st.info("📊 **Отображение данных из базы данных**")
        st.caption(f"Загружено {len(st.session_state.combined_df)} записей из базы данных")
        
        if not st.session_state.all_results:
            st.session_state.all_results = {
                'database_loaded': st.session_state.combined_df.copy()
            }
    
    if data_source == 'file':
        render_file_info(st.session_state.all_results)
    
    # Проверка кодов МКБ-10 (для загруженных данных)
    render_code_validation(st.session_state.all_results)  # ← ОСТАВЛЯЕМ ДЛЯ РАБОТЫ С ДАННЫМИ
    
    st.session_state.combined_df = render_raw_data(
        st.session_state.all_results, 
        st.session_state.combined_df
    )
    
    filtered_df = render_sidebar_filters(
        st.session_state.combined_df, 
        st.session_state.all_results
    )
    
    render_results_table(filtered_df)
    render_summary_stats(filtered_df)
    
    if not filtered_df.empty:
        render_interactive_charts(filtered_df)
        render_standard_charts(filtered_df)
    
    # =========================================================================
    # ЭКСПОРТ
    # =========================================================================
    
    st.subheader("📥 Экспорт результатов")
    
    if not filtered_df.empty:
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Скачать результаты (CSV)",
            data=csv,
            file_name='comorbidity_results.csv',
            mime='text/csv',
            use_container_width=True
        )
        
        if st.button("📊 Скачать Excel (с форматированием)", use_container_width=True):
            with st.spinner("⏳ Генерация Excel-файла..."):
                try:
                    excel_bytes = export_to_excel(filtered_df)
                    st.download_button(
                        label="📊 Скачать Excel-файл",
                        data=excel_bytes,
                        file_name=f'comorbidity_results_{datetime.now().strftime("%Y%m%d")}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True
                    )
                    st.success("✅ Excel-файл готов к скачиванию!")
                except Exception as e:
                    st.error(f"❌ Ошибка при генерации Excel: {str(e)}")
        
        if st.button("📄 Сгенерировать PDF-отчёт", use_container_width=True):
            with st.spinner("⏳ Генерация PDF-отчёта..."):
                try:
                    pdf_bytes = generate_pdf_report(filtered_df)
                    st.download_button(
                        label="📄 Скачать PDF-отчёт",
                        data=pdf_bytes,
                        file_name=f'comorbidity_report_{datetime.now().strftime("%Y%m%d")}.pdf',
                        mime='application/pdf',
                        use_container_width=True
                    )
                    st.success("✅ PDF-отчёт готов к скачиванию!")
                except Exception as e:
                    st.error(f"❌ Ошибка при генерации PDF: {str(e)}")
    
    # =========================================================================
    # ИНФОРМАЦИЯ О СЕССИИ
    # =========================================================================
    
    with st.expander("ℹ️ Информация о сессии"):
        st.write(f"**Источник данных:** {data_source or 'Не указан'}")
        st.write(f"**Всего пациентов:** {len(st.session_state.combined_df)}")
        st.write(f"**Колонки Charlson:** {len(CHARLSON_MAPPINGS)}")
        st.write(f"**Колонки Elixhauser:** {len(ELIXHAUSER_MAPPINGS)}")
        
        if st.session_state.all_results:
            for filename, df in st.session_state.all_results.items():
                st.write(f"- {filename}: {len(df)} пациентов")

else:
    st.info("👆 Загрузите Excel-файлы или загрузите данные из базы данных")
    
    st.markdown("""
    ### 📋 Формат файлов:
    - **Колонка 1:** Patient's ID (текст или число)
    - **Колонка 2:** Patient's ICD-10 codes (коды МКБ-10, разделённые любыми символами)
    
    ### 📊 Что рассчитывается:
    - **Charlson Comorbidity Index** — 17 категорий, 2 варианта весов
    - **Elixhauser Comorbidity Index** — 31 категория, 2 варианта весов
    
    ### 📈 Пример файла:
    | Patient's ID | Patient's ICD-10 codes |
    |--------------|------------------------|
    | 1            | I21.0, E11.9, C50      |
    | 2            | I50, J44, N18          |
    | 3            | F10, K70.0             |
    | 4            | I10, E11.9, E11.7      |
    """)
    
    demo_data = {
        'Patient_ID': ['1', '2', '3', '4', '5'],
        'ICD_codes': [
            'I21.0, E11.9, C50',
            'I50, J44, N18',
            'F10, K70.0',
            'I10, E11.9, E11.7',
            'G45, I63'
        ]
    }
    demo_df = pd.DataFrame(demo_data)
    
    st.markdown("---")
    st.caption("📌 **Пример данных для загрузки:**")
    st.dataframe(demo_df, use_container_width=True, hide_index=True)