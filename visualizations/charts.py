import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from core.charlson import CHARLSON_MAPPINGS
from core.elixhauser import ELIXHAUSER_MAPPINGS
from core.utils import create_comorbidity_heatmap, get_top_diseases, get_top_comorbidity_pairs
from visualizations.utils import normalize_column_names


def render_interactive_charts(filtered_df):
    """Отображает интерактивные графики."""
    if filtered_df.empty:
        return
    
    df = normalize_column_names(filtered_df)
    
    st.subheader("🎯 Интерактивные графики")
    
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
            if 'Source_File' in df.columns:
                color_by = st.selectbox(
                    "Цвет по:",
                    ["Зона риска Charlson", "Зона риска Elixhauser", "Файл"]
                )
            else:
                color_by = st.selectbox(
                    "Цвет по:",
                    ["Зона риска Charlson", "Зона риска Elixhauser"]
                )
    
    if chart_type == "Scatter plot (Charlson vs Elixhauser)":
        render_scatter_plot(df, color_by)
    elif chart_type == "Violin plot (распределение)":
        render_violin_plot(df)
    elif chart_type == "Корреляционная матрица":
        render_correlation_matrix(df)
    elif chart_type == "Радарная диаграмма (выберите пациента)":
        render_radar_chart(df)


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
            
            st.subheader(f"📋 Данные пациента {selected_patient}")
            patient_info = patient_data[['Patient_ID', 'Updated Charlson', 'Charlson Risk', 
                                        'van Walraven Elixhauser', 'Elixhauser Risk']]
            st.dataframe(patient_info, use_container_width=True, hide_index=True)
        else:
            st.warning("Нет данных о заболеваниях для этого пациента")


def render_standard_charts(filtered_df):
    """Отображает стандартные графики."""
    df = normalize_column_names(filtered_df)
    
    st.subheader("📊 Стандартные графики")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Распределение Charlson",
        "📈 Распределение Elixhauser",
        "🏆 Топ заболеваний",
        "🌡️ Тепловая карта"
    ])
    
    with tab1:
        fig = px.histogram(
            df, 
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
            df,
            x='van Walraven Elixhauser',
            title='Распределение индекса van Walraven Elixhauser',
            nbins=20,
            color_discrete_sequence=['#E67E22'],
            labels={'van Walraven Elixhauser': 'Балл Elixhauser', 'count': 'Количество пациентов'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        freq = get_top_diseases(df, CHARLSON_MAPPINGS, 10)
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
                df, CHARLSON_MAPPINGS, "Сочетаемость заболеваний (Charlson)"
            )
            if fig_charlson:
                st.plotly_chart(fig_charlson, use_container_width=True)
            else:
                st.warning("Недостаточно данных")
        
        with col2:
            st.markdown("**Elixhauser**")
            fig_elixhauser = create_comorbidity_heatmap(
                df, ELIXHAUSER_MAPPINGS, "Сочетаемость заболеваний (Elixhauser)"
            )
            if fig_elixhauser:
                st.plotly_chart(fig_elixhauser, use_container_width=True)
            else:
                st.warning("Недостаточно данных")
        
        st.markdown("---")
        st.markdown("### 📊 Частота сочетаемости (топ-5)")
        top_pairs = get_top_comorbidity_pairs(df, CHARLSON_MAPPINGS, 10)
        if top_pairs:
            pair_df = pd.DataFrame(top_pairs, columns=['Частота', 'Заболевание 1', 'Заболевание 2'])
            st.dataframe(pair_df, use_container_width=True, hide_index=True)
        else:
            st.info("Нет данных о сочетаемости заболеваний")