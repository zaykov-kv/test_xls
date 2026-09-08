import streamlit as st
from processing.data_processor import get_file_summary
from visualizations.utils import normalize_column_names


def render_file_info(all_results):
    """Отображает информацию о загруженных файлах."""
    st.subheader("📁 Загруженные файлы")
    file_info_df = get_file_summary(all_results)
    st.dataframe(file_info_df, use_container_width=True, hide_index=True)


def render_loaded_data():
    """Отображает данные, загруженные из базы данных."""
    if 'loaded_data' in st.session_state and st.session_state.loaded_data is not None:
        st.subheader("📊 Загруженные данные из базы данных")
        
        df = normalize_column_names(st.session_state.loaded_data)
        st.dataframe(df, use_container_width=True, height=400)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Всего пациентов", len(df))
        with col2:
            st.metric("📈 Средний Charlson", f"{df['Updated Charlson'].mean():.2f}")
        with col3:
            st.metric("📈 Средний Elixhauser", f"{df['van Walraven Elixhauser'].mean():.2f}")
        
        if st.button("🔄 Очистить загруженные данные", use_container_width=True):
            del st.session_state.loaded_data
            st.rerun()