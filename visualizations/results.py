import streamlit as st
from processing.data_processor import get_comparison_stats
from core.utils import style_dataframe
from visualizations.utils import normalize_column_names


def render_results_table(filtered_df):
    """Отображает таблицу с результатами."""
    st.subheader("📊 Результаты расчёта")
    
    if filtered_df is None or filtered_df.empty:
        st.warning("Нет данных для отображения после применения фильтров")
        return
    
    df = normalize_column_names(filtered_df)
    styled_df = style_dataframe(df)
    st.dataframe(styled_df, use_container_width=True, height=600)
    st.caption("💡 **Итоговые колонки выделены жирным шрифтом и синим фоном**")


def render_summary_stats(filtered_df):
    """Отображает сводную статистику."""
    if filtered_df is None or filtered_df.empty:
        return
    
    df = normalize_column_names(filtered_df)
    
    st.subheader("📈 Сводная статистика")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Средний Charlson (обн.)", f"{df['Updated Charlson'].mean():.2f}")
    with col2:
        st.metric("📊 Макс. Charlson (обн.)", f"{df['Updated Charlson'].max():.0f}")
    with col3:
        st.metric("📈 Средний Elixhauser (vW)", f"{df['van Walraven Elixhauser'].mean():.2f}")
    with col4:
        st.metric("📈 Макс. Elixhauser (vW)", f"{df['van Walraven Elixhauser'].max():.0f}")
    
    if 'Source_File' in df.columns and len(df['Source_File'].unique()) > 1:
        st.subheader("📊 Сравнение по файлам")
        comparison_df = get_comparison_stats(df)
        st.dataframe(comparison_df, use_container_width=True)