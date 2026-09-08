import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from charlson import CHARLSON_MAPPINGS
from elixhauser import ELIXHAUSER_MAPPINGS
from utils import create_comorbidity_heatmap, get_top_diseases, get_top_comorbidity_pairs
from analysis import get_file_summary, get_comparison_stats
from icd_api import get_icd10_code_details
from database_supabase import SupabaseManager


def render_file_info(all_results):
    """Отображает информацию о загруженных файлах."""
    st.subheader("📁 Загруженные файлы")
    file_info_df = get_file_summary(all_results)
    st.dataframe(file_info_df, use_container_width=True, hide_index=True)


def render_raw_data(all_results, combined_df):
    """
    Отображает исходные данные с возможностью редактирования.
    """
    with st.expander("📋 Редактирование исходных данных", expanded=False):
        st.markdown("**✏️ Редактирование данных пациентов**")
        st.caption("💡 Вы можете редактировать ID пациента и коды МКБ-10. После сохранения данные будут пересчитаны автоматически.")
        
        # Проверка наличия данных
        if not all_results:
            st.warning("Нет данных для редактирования")
            return combined_df
        
        if combined_df is None or combined_df.empty:
            st.warning("Нет данных для редактирования")
            return combined_df
        
        # --- ПРИВОДИМ ТИПЫ ПЕРЕД РЕДАКТИРОВАНИЕМ ---
        combined_df = combined_df.copy()
        if 'Patient_ID' in combined_df.columns:
            combined_df['Patient_ID'] = combined_df['Patient_ID'].astype(str)
        if 'ICD_codes' in combined_df.columns:
            combined_df['ICD_codes'] = combined_df['ICD_codes'].astype(str)
        if 'Source_File' in combined_df.columns:
            combined_df['Source_File'] = combined_df['Source_File'].astype(str)
        # --- КОНЕЦ ПРИВЕДЕНИЯ ТИПОВ ---
        
        # Выбор файла для редактирования
        files = list(all_results.keys())
        if not files:
            st.warning("Нет загруженных файлов")
            return combined_df
        
        selected_file = st.selectbox(
            "Выберите файл для редактирования:",
            options=files,
            index=0
        )
        
        if selected_file and selected_file in all_results:
            # Получаем данные выбранного файла
            file_df = all_results[selected_file].copy()
            
            # Приводим типы в файле
            if 'Patient_ID' in file_df.columns:
                file_df['Patient_ID'] = file_df['Patient_ID'].astype(str)
            if 'ICD_codes' in file_df.columns:
                file_df['ICD_codes'] = file_df['ICD_codes'].astype(str)
            
            # Показываем только исходные колонки
            edit_df = file_df[['Source_File', 'Patient_ID', 'ICD_codes']].copy()
            
            # Выбор количества записей для отображения
            show_n = st.selectbox(
                "Показывать записей:",
                options=[5, 10, 20, 50, 100, 0],
                format_func=lambda x: "Все" if x == 0 else str(x),
                index=1,
                key="edit_show_n"
            )
            
            # Отображаем редактируемую таблицу
            st.markdown(f"**Редактирование файла: {selected_file}**")
            
            if show_n == 0:
                display_df = edit_df.copy()
            else:
                display_df = edit_df.head(show_n).copy()
            
            # Редактируемая таблица
            edited_df = st.data_editor(
                display_df,
                num_rows="dynamic",
                use_container_width=True,
                height=400,
                column_config={
                    "Source_File": st.column_config.TextColumn(
                        "Источник",
                        help="Имя файла",
                        disabled=True
                    ),
                    "Patient_ID": st.column_config.TextColumn(
                        "ID пациента",
                        help="Введите ID пациента",
                        required=True
                    ),
                    "ICD_codes": st.column_config.TextColumn(
                        "Коды МКБ-10",
                        help="Введите коды через разделители (запятая, точка с запятой, пробел)",
                        required=True
                    )
                }
            )
            
            # Кнопка для сохранения изменений
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("💾 Сохранить и пересчитать", use_container_width=True, type="primary"):
                    # Обновляем данные
                    try:
                        # Сохраняем изменения в оригинальный DataFrame
                        for idx, row in edited_df.iterrows():
                            patient_id = row['Patient_ID']
                            icd_codes = row['ICD_codes']
                            
                            # Пропускаем пустые строки
                            if pd.isna(patient_id) or str(patient_id).strip() == '':
                                continue
                            
                            # Находим соответствующую строку в оригинальном DataFrame
                            mask = (file_df['Patient_ID'].astype(str) == str(patient_id)) & (file_df['Source_File'] == selected_file)
                            if mask.any():
                                # Обновляем существующую запись
                                file_df.loc[mask, 'ICD_codes'] = icd_codes
                            else:
                                # Добавляем новую запись
                                new_row = {col: 0 for col in file_df.columns}
                                new_row['Source_File'] = selected_file
                                new_row['Patient_ID'] = str(patient_id)
                                new_row['ICD_codes'] = icd_codes
                                file_df = pd.concat([file_df, pd.DataFrame([new_row])], ignore_index=True)
                        
                        # Удаляем строки с пустым ID
                        file_df = file_df[file_df['Patient_ID'].astype(str).str.strip() != '']
                        
                        # Обновляем all_results
                        all_results[selected_file] = file_df
                        
                        # Пересчитываем результаты для этого файла
                        with st.spinner("⏳ Пересчёт данных..."):
                            from analysis import calculate_patients, add_risk_zones
                            
                            # Подготовка данных для расчёта
                            calc_df = file_df[['Patient_ID', 'ICD_codes']].copy()
                            new_results = calculate_patients(calc_df, selected_file)
                            new_result_df = pd.DataFrame(new_results)
                            new_result_df = add_risk_zones(new_result_df)
                            
                            # Обновляем все результаты
                            all_results[selected_file] = new_result_df
                            
                            # Обновляем combined_df
                            updated_combined = []
                            for fname, fdf in all_results.items():
                                updated_combined.append(fdf)
                            if updated_combined:
                                new_combined = pd.concat(updated_combined, ignore_index=True)
                                
                                # Сохраняем в сессию
                                st.session_state['combined_df'] = new_combined
                                st.session_state['all_results'] = all_results
                                
                                st.success(f"✅ Данные для файла '{selected_file}' обновлены и пересчитаны!")
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Ошибка при сохранении: {str(e)}")
            
            with col2:
                if st.button("➕ Добавить строку", use_container_width=True):
                    new_row = pd.DataFrame({
                        'Source_File': [selected_file],
                        'Patient_ID': [''],
                        'ICD_codes': ['']
                    })
                    edited_df = pd.concat([edited_df, new_row], ignore_index=True)
                    st.rerun()
            
            with col3:
                st.info(f"📊 Всего записей в файле: {len(file_df)}")
            
            with st.expander("🔄 Предпросмотр обновлённых данных"):
                st.dataframe(file_df[['Patient_ID', 'ICD_codes']].head(10), use_container_width=True)
                if len(file_df) > 10:
                    st.caption(f"Показано 10 из {len(file_df)} записей")
    
    # Возвращаем обновлённый combined_df из сессии
    if 'combined_df' in st.session_state:
        return st.session_state['combined_df']
    
    return combined_df


def render_score_slider(filtered_df, index_type='Charlson'):
    """
    Отображает слайдер для фильтрации по баллам.
    
    Args:
        filtered_df: DataFrame с данными
        index_type: 'Charlson' или 'Elixhauser'
    """
    if filtered_df is None or filtered_df.empty:
        return filtered_df
    
    if index_type == 'Charlson':
        score_col = 'Updated Charlson'
        label = "Диапазон баллов Charlson"
    else:  # Elixhauser
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
    """
    Отображает фильтры в боковой панели и возвращает отфильтрованный DataFrame.
    """
    st.sidebar.header("🔍 Фильтры и поиск")
    
    # Если данных нет, показываем сообщение
    if combined_df is None or combined_df.empty:
        st.sidebar.warning("Нет данных для фильтрации")
        return combined_df
    
    # --- ВЫБОР ФАЙЛА (если есть) ---
    if all_results and len(all_results) > 1:
        selected_files = st.sidebar.multiselect(
            "Выберите файлы для анализа",
            options=list(all_results.keys()),
            default=list(all_results.keys())
        )
        filtered_df = combined_df[combined_df['Source_File'].isin(selected_files)] if selected_files else combined_df
    else:
        filtered_df = combined_df
    
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
    
    # --- ФИЛЬТР ПО ЗОНЕ РИСКА ELIXHAUSER (ВОЗВРАЩАЕМ) ---
    risk_filter_elix = st.sidebar.multiselect(
        "Зона риска Elixhauser",
        options=['🟢 Низкий', '🟡 Средний', '🟠 Высокий', '🔴 Очень высокий'],
        default=['🟢 Низкий', '🟡 Средний', '🟠 Высокий', '🔴 Очень высокий']
    )
    if risk_filter_elix:
        filtered_df = filtered_df[filtered_df['Elixhauser Risk'].isin(risk_filter_elix)]
    
    # --- ФИЛЬТР ПО ДИАПАЗОНУ БАЛЛОВ CHARLSON ---
    if not filtered_df.empty:
        filtered_df = render_score_slider(filtered_df, 'Charlson')
    
    # --- ФИЛЬТР ПО ДИАПАЗОНУ БАЛЛОВ ELIXHAUSER ---
    if not filtered_df.empty:
        filtered_df = render_score_slider(filtered_df, 'Elixhauser')
    
    st.sidebar.markdown("---")
    st.sidebar.metric("📊 Найдено пациентов", len(filtered_df) if filtered_df is not None else 0)
    
    return filtered_df


def render_results_table(filtered_df):
    """Отображает таблицу с результатами."""
    from utils import style_dataframe
    
    st.subheader("📊 Результаты расчёта")
    
    if filtered_df is None or filtered_df.empty:
        st.warning("Нет данных для отображения после применения фильтров")
        return
    
    styled_df = style_dataframe(filtered_df)
    st.dataframe(styled_df, use_container_width=True, height=600)
    st.caption("💡 **Итоговые колонки выделены жирным шрифтом и синим фоном**")


def render_summary_stats(filtered_df):
    """Отображает сводную статистику."""
    if filtered_df is None or filtered_df.empty:
        return
    
    st.subheader("📈 Сводная статистика")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Средний Charlson (обн.)", f"{filtered_df['Updated Charlson'].mean():.2f}")
    with col2:
        st.metric("📊 Макс. Charlson (обн.)", f"{filtered_df['Updated Charlson'].max():.0f}")
    with col3:
        st.metric("📈 Средний Elixhauser (vW)", f"{filtered_df['van Walraven Elixhauser'].mean():.2f}")
    with col4:
        st.metric("📈 Макс. Elixhauser (vW)", f"{filtered_df['van Walraven Elixhauser'].max():.0f}")
    
    # Сравнение по файлам (если есть несколько)
    if 'Source_File' in filtered_df.columns and len(filtered_df['Source_File'].unique()) > 1:
        st.subheader("📊 Сравнение по файлам")
        comparison_df = get_comparison_stats(filtered_df)
        st.dataframe(comparison_df, use_container_width=True)


def render_interactive_charts(filtered_df):
    """Отображает интерактивные графики."""
    if filtered_df.empty:
        return
    
    st.subheader("🎯 Интерактивные графики")
    
    # Настройки
    with st.expander("⚙️ Настройки графиков", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            chart_type = st.selectbox(
                "Тип графика",
                [
                    "Scatter plot (Charlson vs Elixhauser)",
                    "Violin plot (распределение)",
                    "Корреляционная матрица",
                    "Радарная диаграмма (выберите пациента)"
                ]
            )
        with col2:
            if 'Source_File' in filtered_df.columns:
                color_by = st.selectbox(
                    "Цвет по:",
                    ["Зона риска Charlson", "Зона риска Elixhauser", "Файл"]
                )
            else:
                color_by = st.selectbox(
                    "Цвет по:",
                    ["Зона риска Charlson", "Зона риска Elixhauser"]
                )
    
    # Выбор графика
    if chart_type == "Scatter plot (Charlson vs Elixhauser)":
        render_scatter_plot(filtered_df, color_by)
    elif chart_type == "Violin plot (распределение)":
        render_violin_plot(filtered_df)
    elif chart_type == "Корреляционная матрица":
        render_correlation_matrix(filtered_df)
    elif chart_type == "Радарная диаграмма (выберите пациента)":
        render_radar_chart(filtered_df)


def render_scatter_plot(filtered_df, color_by):
    """Scatter plot: Charlson vs Elixhauser."""
    color_map = {
        "Зона риска Charlson": "Charlson Risk",
        "Зона риска Elixhauser": "Elixhauser Risk",
        "Файл": "Source_File"
    }
    color_col = color_map.get(color_by, "Charlson Risk")
    
    fig = px.scatter(
        filtered_df,
        x='Updated Charlson',
        y='van Walraven Elixhauser',
        color=color_col,
        title='Зависимость индексов коморбидности',
        labels={
            'Updated Charlson': 'Charlson (обн.)',
            'van Walraven Elixhauser': 'Elixhauser (vW)'
        },
        hover_data=['Patient_ID'] + (['Source_File'] if 'Source_File' in filtered_df.columns else []),
        size='Updated Charlson',
        size_max=20,
        opacity=0.7
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Корреляция
    corr = filtered_df['Updated Charlson'].corr(filtered_df['van Walraven Elixhauser'])
    st.info(f"📊 Корреляция между индексами: {corr:.3f}")


def render_violin_plot(filtered_df):
    """Violin plot распределения."""
    if 'Source_File' in filtered_df.columns and len(filtered_df['Source_File'].unique()) > 1:
        fig = px.violin(
            filtered_df,
            x='Source_File',
            y='Updated Charlson',
            color='Charlson Risk',
            box=True,
            points='all',
            title='Распределение Charlson по файлам и зонам риска',
            labels={'Updated Charlson': 'Charlson (обн.)', 'Source_File': 'Файл'}
        )
        fig.update_layout(height=500)
    else:
        fig = px.violin(
            filtered_df,
            y='Updated Charlson',
            color='Charlson Risk',
            box=True,
            points='all',
            title='Распределение Charlson по зонам риска',
            labels={'Updated Charlson': 'Charlson (обн.)'}
        )
        fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_matrix(filtered_df):
    """Корреляционная матрица заболеваний."""
    available_cols = [col for col in CHARLSON_MAPPINGS.keys() if col in filtered_df.columns]
    selected_cols = st.multiselect(
        "Выберите заболевания для матрицы корреляции:",
        options=available_cols,
        default=available_cols[:10] if len(available_cols) > 10 else available_cols
    )
    
    if selected_cols and len(selected_cols) > 1:
        corr_matrix = filtered_df[selected_cols].corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu_r',
            zmin=-1,
            zmax=1,
            text=np.round(corr_matrix.values, 2),
            texttemplate='%{text:.2f}',
            textfont={"size": 8}
        ))
        fig.update_layout(
            title='Корреляционная матрица заболеваний',
            height=600,
            xaxis={'tickangle': 45, 'tickfont': {'size': 9}},
            yaxis={'tickfont': {'size': 9}},
            margin=dict(l=50, r=50, t=80, b=200)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Выберите хотя бы 2 заболевания для построения матрицы")


def render_radar_chart(filtered_df):
    """Радарная диаграмма для выбранного пациента."""
    if filtered_df.empty or 'Patient_ID' not in filtered_df.columns:
        st.warning("Нет данных о пациентах")
        return
    
    selected_patient = st.selectbox(
        "Выберите пациента для радарной диаграммы:",
        options=filtered_df['Patient_ID'].tolist()
    )
    
    if selected_patient:
        patient_data = filtered_df[filtered_df['Patient_ID'] == selected_patient]
        categories = [col for col in CHARLSON_MAPPINGS.keys() if col in filtered_df.columns]
        
        if categories:
            values = [patient_data[col].values[0] for col in categories]
            
            fig = go.Figure(data=go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=selected_patient,
                line_color='#2E86C1',
                fillcolor='rgba(46, 134, 193, 0.3)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 1],
                        tickvals=[0, 1],
                        ticktext=['Нет', 'Есть']
                    )
                ),
                title=f'Профиль коморбидности: {selected_patient}',
                height=500,
                margin=dict(l=80, r=80, t=80, b=80)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Информация о пациенте
            st.subheader(f"📋 Данные пациента {selected_patient}")
            patient_info = patient_data[['Patient_ID', 'Updated Charlson', 'Charlson Risk', 
                                        'van Walraven Elixhauser', 'Elixhauser Risk']]
            st.dataframe(patient_info, use_container_width=True, hide_index=True)
        else:
            st.warning("Нет данных о заболеваниях для этого пациента")


def render_standard_charts(filtered_df):
    """Отображает стандартные графики."""
    st.subheader("📊 Стандартные графики")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Распределение Charlson",
        "📈 Распределение Elixhauser",
        "🏆 Топ заболеваний",
        "🌡️ Тепловая карта"
    ])
    
    with tab1:
        fig = px.histogram(
            filtered_df, 
            x='Updated Charlson',
            title='Распределение обновлённого индекса Charlson',
            nbins=20,
            color_discrete_sequence=['#2E86C1'],
            labels={'Updated Charlson': 'Балл Charlson', 'count': 'Количество пациентов'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = px.histogram(
            filtered_df,
            x='van Walraven Elixhauser',
            title='Распределение индекса van Walraven Elixhauser',
            nbins=20,
            color_discrete_sequence=['#E67E22'],
            labels={'van Walraven Elixhauser': 'Балл Elixhauser', 'count': 'Количество пациентов'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        freq = get_top_diseases(filtered_df, CHARLSON_MAPPINGS, 10)
        if not freq.empty:
            fig = px.bar(
                x=freq.values,
                y=freq.index,
                orientation='h',
                title='Топ-10 заболеваний (Charlson)',
                labels={'x': 'Количество пациентов', 'y': 'Заболевание'},
                color=freq.values,
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о заболеваниях")
    
    with tab4:
        st.markdown("### 🌡️ Тепловая карта сочетаемости заболеваний")
        st.caption("Коэффициент Жаккара показывает, как часто два заболевания встречаются вместе.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Charlson**")
            fig_charlson = create_comorbidity_heatmap(
                filtered_df, CHARLSON_MAPPINGS, "Сочетаемость заболеваний (Charlson)"
            )
            if fig_charlson:
                st.plotly_chart(fig_charlson, use_container_width=True)
            else:
                st.warning("Недостаточно данных")
        
        with col2:
            st.markdown("**Elixhauser**")
            fig_elixhauser = create_comorbidity_heatmap(
                filtered_df, ELIXHAUSER_MAPPINGS, "Сочетаемость заболеваний (Elixhauser)"
            )
            if fig_elixhauser:
                st.plotly_chart(fig_elixhauser, use_container_width=True)
            else:
                st.warning("Недостаточно данных")
        
        st.markdown("---")
        st.markdown("### 📊 Частота сочетаемости (топ-5)")
        top_pairs = get_top_comorbidity_pairs(filtered_df, CHARLSON_MAPPINGS, 10)
        if top_pairs:
            pair_df = pd.DataFrame(top_pairs, columns=['Частота', 'Заболевание 1', 'Заболевание 2'])
            st.dataframe(pair_df, use_container_width=True, hide_index=True)
        else:
            st.info("Нет данных о сочетаемости заболеваний")

def render_code_validation(all_results):
    """
    Поиск информации о конкретном коде МКБ-10 через API.
    """
    with st.expander("🔍 Проверка кода МКБ-10", expanded=False):
        st.markdown("**Поиск информации о коде МКБ-10**")
        st.caption("💡 Введите код для проверки (например, E11.9, I10, C50)")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            icd_code = st.text_input(
                "Введите код МКБ-10:",
                placeholder="Например: E11.9, I10, C50",
                key="icd_code_search"
            )
        
        with col2:
            search_btn = st.button("🔍 Найти код", use_container_width=True, type="primary")
        
        if search_btn and icd_code:
            with st.spinner("⏳ Поиск кода..."):
                code_clean = icd_code.strip().upper()
                details = get_icd10_code_details(code_clean)
                
                if details:
                    st.success(f"✅ Код **{code_clean}** найден")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📋 Код", details.get("code", code_clean))
                    with col2:
                        st.metric("📝 Статус", "✅ Корректен")
                    
                    st.info(f"**Описание:** {details.get('description', 'Описание не найдено')}")
                else:
                    st.warning(f"❌ Код **{code_clean}** не найден. Проверьте правильность ввода.")
        
        # Быстрый доступ к часто используемым кодам
        st.markdown("---")
        st.markdown("**📌 Часто используемые коды:**")
        
        common_codes = [
            ("E11.9", "Сахарный диабет 2 типа без осложнений"),
            ("I10", "Эссенциальная гипертензия"),
            ("I50", "Сердечная недостаточность"),
            ("J44", "Хроническая обструктивная болезнь легких"),
            ("C50", "Злокачественное новообразование молочной железы"),
            ("N18", "Хроническая почечная недостаточность"),
            ("F10", "Алкоголизм"),
            ("E66", "Ожирение")
        ]
        
        cols = st.columns(4)
        for idx, (code, desc) in enumerate(common_codes):
            with cols[idx % 4]:
                if st.button(f"📋 {code}", key=f"common_{code}"):
                    st.session_state.icd_code_search = code
                    st.rerun()


def render_code_validation(all_results):
    """
    Поиск информации о конкретном коде МКБ-10 через API.
    """
    with st.expander("🔍 Проверка кода МКБ-10", expanded=False):
        st.markdown("**Поиск информации о коде МКБ-10**")
        st.caption("💡 Введите код для проверки (например, E11.9, I10, C50)")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            icd_code = st.text_input(
                "Введите код МКБ-10:",
                placeholder="Например: E11.9, I10, C50",
                key="icd_code_search"
            )
        
        with col2:
            search_btn = st.button("🔍 Найти код", use_container_width=True, type="primary")
        
        if search_btn and icd_code:
            # Импортируем только нужную функцию
            from icd_api import get_icd10_code_details
            
            with st.spinner("⏳ Поиск кода..."):
                code_clean = icd_code.strip().upper()
                details = get_icd10_code_details(code_clean)
                
                if details:
                    st.success(f"✅ Код **{code_clean}** найден")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📋 Код", details.get("code", code_clean))
                    with col2:
                        st.metric("📝 Статус", "✅ Корректен")
                    
                    st.info(f"**Описание:** {details.get('description', 'Описание не найдено')}")
                else:
                    st.warning(f"❌ Код **{code_clean}** не найден. Проверьте правильность ввода.")
        
        # Быстрый доступ к часто используемым кодам
        st.markdown("---")
        st.markdown("**📌 Часто используемые коды:**")
        
        common_codes = [
            ("E11.9", "Сахарный диабет 2 типа без осложнений"),
            ("I10", "Эссенциальная гипертензия"),
            ("I50", "Сердечная недостаточность"),
            ("J44", "Хроническая обструктивная болезнь легких"),
            ("C50", "Злокачественное новообразование молочной железы"),
            ("N18", "Хроническая почечная недостаточность"),
            ("F10", "Алкоголизм"),
            ("E66", "Ожирение")
        ]
        
        cols = st.columns(4)
        for idx, (code, desc) in enumerate(common_codes):
            with cols[idx % 4]:
                if st.button(f"📋 {code}", key=f"common_{code}"):
                    st.session_state.icd_code_search = code
                    st.rerun()

from database import DatabaseManager


def render_database_interface():
    """
    Отображает интерфейс для работы с базой данных.
    """
    with st.expander("💾 Сохранение и загрузка данных (База данных)", expanded=False):
        db = SupabaseManager()
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "💾 Сохранить текущие данные",
            "📂 Загрузить данные",
            "📊 История сессий",
            "🔍 Поиск пациентов"
        ])
        
        # --- Вкладка 1: Сохранение ---
        with tab1:
            st.markdown("**Сохранить текущие данные в базу данных**")
            st.caption("💡 Будут сохранены все результаты расчёта для текущей сессии")
            
            # Проверяем наличие данных
            has_data = (
                'all_results' in st.session_state and 
                st.session_state.all_results and 
                st.session_state.combined_df is not None and
                not st.session_state.combined_df.empty
            )
            
            if not has_data:
                st.warning("Нет данных для сохранения. Сначала загрузите файлы.")
                st.info("💡 Загрузите Excel-файлы с ID пациента и кодами МКБ-10")
            else:
                combined_df = st.session_state.combined_df
                
                if combined_df is not None and not combined_df.empty:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        save_name = st.text_input(
                            "Название сессии:",
                            value=f"Анализ_{datetime.now().strftime('%d.%m.%Y_%H%M')}",
                            key="save_session_name"
                        )
                    
                    with col2:
                        if st.button("💾 Сохранить в базу данных", use_container_width=True, type="primary"):
                            with st.spinner("⏳ Сохранение данных..."):
                                try:
                                    session_id = db.save_session(combined_df, save_name)
                                    st.success(f"✅ Данные сохранены! ID сессии: {session_id}")
                                    st.balloons()
                                except Exception as e:
                                    st.error(f"❌ Ошибка при сохранении: {str(e)}")
                    
                    st.info(f"📊 Будет сохранено {len(combined_df)} пациентов")
        # Вкладка 2: Загрузка
        with tab2:
            st.markdown("**Загрузить ранее сохранённые данные**")
            
            with st.spinner("⏳ Загрузка списка сессий..."):
                sessions = db.get_sessions(limit=20)
            
            if sessions.empty:
                st.warning("Нет сохранённых сессий в базе данных")
                st.info("💡 Сначала сохраните данные через вкладку 'Сохранить текущие данные'")
            else:
                st.success(f"✅ Найдено {len(sessions)} сессий")
                # Показываем список сессий
                session_options = {
                    f"{row['session_id']} - {row['file_name']} ({row['created_at'][:16]})": row['session_id']
                    for _, row in sessions.iterrows()
                }
                
                selected_session = st.selectbox(
                    "Выберите сессию для загрузки:",
                    options=list(session_options.keys()),
                    key="load_session_select"
                )
                
                if selected_session:
                    session_id = session_options[selected_session]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📂 Загрузить данные", use_container_width=True, type="primary"):
                            with st.spinner("⏳ Загрузка данных..."):
                                df = db.get_session_data(session_id)
                                if df is not None and not df.empty:
                                    # Сохраняем в сессию как основные данные
                                    st.session_state.combined_df = df
                                    st.session_state.all_results = {'loaded_from_db': df}
                                    st.session_state.data_source = 'database'
                                    st.session_state.uploaded_files_processed = True
                                    st.success(f"✅ Загружено {len(df)} пациентов из базы данных")
                                    st.rerun()
                                else:
                                    st.error("❌ Ошибка при загрузке данных")
                    
                    with col2:
                        if st.button("🗑️ Удалить сессию", use_container_width=True):
                            if db.delete_session(session_id):
                                st.success("✅ Сессия удалена")
                                st.rerun()
                            else:
                                st.error("❌ Ошибка при удалении")
                
                # Предпросмотр сессий
                with st.expander("📋 Список всех сессий"):
                    st.dataframe(
                        sessions[['session_id', 'created_at', 'file_name', 'total_patients', 'avg_charlson']],
                        use_container_width=True,
                        hide_index=True
                    )

def render_loaded_data():
    """
    Отображает данные, загруженные из базы данных.
    """
    if 'loaded_data' in st.session_state and st.session_state.loaded_data is not None:
        st.subheader("📊 Загруженные данные из базы данных")
        
        df = st.session_state.loaded_data
        st.dataframe(df, use_container_width=True, height=400)
        
        # Статистика
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Всего пациентов", len(df))
        with col2:
            st.metric("📈 Средний Charlson", f"{df['Updated Charlson'].mean():.2f}")
        with col3:
            st.metric("📈 Средний Elixhauser", f"{df['van Walraven Elixhauser'].mean():.2f}")
        
        # Кнопка для очистки загруженных данных
        if st.button("🔄 Очистить загруженные данные", use_container_width=True):
            del st.session_state.loaded_data
            st.rerun()