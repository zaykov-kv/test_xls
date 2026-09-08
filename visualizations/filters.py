import streamlit as st
from visualizations.utils import normalize_column_names


def render_score_slider(filtered_df, index_type='Charlson'):
    """Отображает слайдер для фильтрации по баллам."""
    if filtered_df is None or filtered_df.empty:
        return filtered_df
    
    if index_type == 'Charlson':
        score_col = 'Updated Charlson'
        label = "Диапазон баллов Charlson"
    else:
        score_col = 'van Walraven Elixhauser'
        label = "Диапазон баллов Elixhauser"
    
    min_score = int(filtered_df[score_col].min())
    max_score = int(filtered_df[score_col].max())
    
    if min_score == max_score:
        st.sidebar.info(f"ℹ️ Все пациенты имеют одинаковый балл {index_type} = {min_score}")
        score_range = st.sidebar.slider(
            label,
            min_value=min_score,
            max_value=min_score + 1,
            value=(min_score, min_score + 1)
        )
        return filtered_df[filtered_df[score_col] == min_score]
    else:
        score_range = st.sidebar.slider(
            label,
            min_value=min_score,
            max_value=max_score,
            value=(min_score, max_score)
        )
        return filtered_df[(filtered_df[score_col] >= score_range[0]) & 
                          (filtered_df[score_col] <= score_range[1])]


def render_sidebar_filters(combined_df, all_results):
    """Отображает фильтры в боковой панели."""
    st.sidebar.header("🔍 Фильтры и поиск")
    
    if combined_df is None or combined_df.empty:
        st.sidebar.warning("Нет данных для фильтрации")
        return combined_df
    
    df = normalize_column_names(combined_df)
    
    # --- ВЫБОР ФАЙЛА ---
    if all_results and len(all_results) > 1:
        selected_files = st.sidebar.multiselect(
            "Выберите файлы для анализа",
            options=list(all_results.keys()),
            default=list(all_results.keys())
        )
        filtered_df = df[df['Source_File'].isin(selected_files)] if selected_files else df
    else:
        filtered_df = df
    
    # Поиск по ID
    search_id = st.sidebar.text_input("Поиск по ID пациента")
    if search_id:
        filtered_df = filtered_df[filtered_df['Patient_ID'].astype(str).str.contains(search_id, case=False)]
    
    # --- ФИЛЬТР ПО ЗОНЕ РИСКА CHARLSON ---
    risk_filter = st.sidebar.multiselect(
        "Зона риска Charlson",
        options=['🟢 Низкий', '🟡 Средний', '🟠 Высокий', '🔴 Очень высокий'],
        default=['🟢 Низкий', '🟡 Средний', '🟠 Высокий', '🔴 Очень высокий']
    )
    if risk_filter:
        filtered_df = filtered_df[filtered_df['Charlson Risk'].isin(risk_filter)]
    
    # --- ФИЛЬТР ПО ЗОНЕ РИСКА ELIXHAUSER ---
    risk_filter_elix = st.sidebar.multiselect(
        "Зона риска Elixhauser",
        options=['🟢 Низкий', '🟡 Средний', '🟠 Высокий', '🔴 Очень высокий'],
        default=['🟢 Низкий', '🟡 Средний', '🟠 Высокий', '🔴 Очень высокий']
    )
    if risk_filter_elix:
        filtered_df = filtered_df[filtered_df['Elixhauser Risk'].isin(risk_filter_elix)]
    
    # --- ФИЛЬТР ПО ДИАПАЗОНУ БАЛЛОВ ---
    if not filtered_df.empty:
        filtered_df = render_score_slider(filtered_df, 'Charlson')
    
    if not filtered_df.empty:
        filtered_df = render_score_slider(filtered_df, 'Elixhauser')
    
    st.sidebar.markdown("---")
    st.sidebar.metric("📊 Найдено пациентов", len(filtered_df) if filtered_df is not None else 0)
    
    return filtered_df