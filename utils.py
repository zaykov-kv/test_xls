import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from charlson import CHARLSON_MAPPINGS
from elixhauser import ELIXHAUSER_MAPPINGS

def add_risk_zones(df):
    """
    Добавляет колонки с зонами риска для индексов Charlson и Elixhauser.
    """
    def charlson_risk(score):
        if score <= 1:
            return '🟢 Низкий'
        elif score <= 3:
            return '🟡 Средний'
        elif score <= 5:
            return '🟠 Высокий'
        else:
            return '🔴 Очень высокий'
    
    def elixhauser_risk(score):
        if score < -5:
            return '🟢 Низкий'
        elif score <= 5:
            return '🟡 Средний'
        elif score <= 15:
            return '🟠 Высокий'
        else:
            return '🔴 Очень высокий'
    
    df['Charlson Risk'] = df['Updated Charlson'].apply(charlson_risk)
    df['Elixhauser Risk'] = df['van Walraven Elixhauser'].apply(elixhauser_risk)
    return df


def create_comorbidity_heatmap(df, mappings, title):
    """
    Создаёт тепловую карту корреляции заболеваний.
    """
    categories = list(mappings.keys())
    available_cols = [col for col in categories if col in df.columns]
    
    if len(available_cols) < 2:
        return None
    
    data = df[available_cols].values
    n_cats = len(available_cols)
    jaccard_matrix = np.zeros((n_cats, n_cats))
    
    for i in range(n_cats):
        for j in range(n_cats):
            if i == j:
                jaccard_matrix[i, j] = 1
            else:
                intersection = np.sum((data[:, i] == 1) & (data[:, j] == 1))
                union = np.sum((data[:, i] == 1) | (data[:, j] == 1))
                if union > 0:
                    jaccard_matrix[i, j] = intersection / union
                else:
                    jaccard_matrix[i, j] = 0
    
    fig = go.Figure(data=go.Heatmap(
        z=jaccard_matrix,
        x=available_cols,
        y=available_cols,
        colorscale='Reds',
        zmin=0,
        zmax=0.5,
        text=np.round(jaccard_matrix, 2),
        texttemplate='%{text:.2f}',
        textfont={"size": 8},
        hovertemplate='%{x} ↔ %{y}<br>Коэффициент: %{z:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        width=900,
        height=800,
        xaxis={'tickangle': 45, 'tickfont': {'size': 9}},
        yaxis={'tickfont': {'size': 9}},
        margin=dict(l=50, r=50, t=80, b=200),
        coloraxis_colorbar=dict(
            title="Коэффициент<br>Жаккара",
            tickvals=[0, 0.1, 0.2, 0.3, 0.4, 0.5],
            ticktext=["0", "0.1", "0.2", "0.3", "0.4", "0.5+"]
        )
    )
    return fig


def get_final_columns():
    """Возвращает список итоговых колонок."""
    return [
        'Original Charlson', 
        'Updated Charlson',
        'Charlson Risk',
        'AHRQ Elixhauser', 
        'van Walraven Elixhauser',
        'Elixhauser Risk'
    ]


def style_dataframe(df):
    """Стилизация DataFrame для отображения в Streamlit."""
    final_columns = get_final_columns()
    existing_final_cols = [col for col in final_columns if col in df.columns]
    
    def style_cell(val, col_name):
        if col_name in existing_final_cols:
            return 'font-weight: bold; background-color: #e6f3ff; border-left: 2px solid #2196F3; border-right: 2px solid #2196F3;'
        return ''
    
    styled = df.style
    
    for col in existing_final_cols:
        styled = styled.apply(lambda x: ['font-weight: bold; background-color: #e6f3ff; border-left: 2px solid #2196F3; border-right: 2px solid #2196F3;' if i in x.index else '' for i in x.index], subset=[col], axis=0)
    
    risk_colors = {
        '🟢 Низкий': 'background-color: #d4edda; font-weight: bold;',
        '🟡 Средний': 'background-color: #fff3cd; font-weight: bold;',
        '🟠 Высокий': 'background-color: #ffe5b4; font-weight: bold;',
        '🔴 Очень высокий': 'background-color: #f8d7da; font-weight: bold;'
    }
    
    if 'Charlson Risk' in df.columns:
        styled = styled.apply(lambda x: [risk_colors.get(val, '') for val in x], subset=['Charlson Risk'], axis=0)
    
    if 'Elixhauser Risk' in df.columns:
        styled = styled.apply(lambda x: [risk_colors.get(val, '') for val in x], subset=['Elixhauser Risk'], axis=0)
    
    return styled


def get_top_diseases(df, mappings, n=10):
    """Возвращает топ-N заболеваний по частоте."""
    cols = [col for col in mappings.keys() if col in df.columns]
    if not cols:
        return pd.Series()
    return df[cols].sum().sort_values(ascending=False).head(n)


def get_top_comorbidity_pairs(df, mappings, n=10):
    """Возвращает топ-N пар заболеваний, встречающихся вместе."""
    cols = [col for col in mappings.keys() if col in df.columns]
    pairs = []
    for i in range(len(cols)):
        for j in range(i+1, len(cols)):
            both = ((df[cols[i]] == 1) & (df[cols[j]] == 1)).sum()
            if both > 0:
                pairs.append((both, cols[i], cols[j]))
    pairs.sort(reverse=True)
    return pairs[:n]
# Добавьте в конец файла utils.py

def create_interactive_charts(df):
    """
    Создаёт набор интерактивных графиков для анализа данных.
    """
    charts = {}
    
    # 1. Scatter plot: Charlson vs Elixhauser с цветовой индикацией
    fig_scatter = px.scatter(
        df,
        x='Updated Charlson',
        y='van Walraven Elixhauser',
        color='Charlson Risk',
        title='Зависимость Charlson от Elixhauser',
        labels={
            'Updated Charlson': 'Charlson (обн.)',
            'van Walraven Elixhauser': 'Elixhauser (vW)'
        },
        hover_data=['Patient_ID', 'Source_File'] if 'Source_File' in df.columns else ['Patient_ID'],
        color_discrete_map={
            '🟢 Низкий': '#28a745',
            '🟡 Средний': '#ffc107',
            '🟠 Высокий': '#fd7e14',
            '🔴 Очень высокий': '#dc3545'
        },
        opacity=0.7,
        size='Updated Charlson',
        size_max=20
    )
    fig_scatter.update_layout(height=450)
    charts['scatter'] = fig_scatter
    
    # 2. Violin plot: Распределение по группам риска
    if 'Source_File' in df.columns and len(df['Source_File'].unique()) > 1:
        fig_violin = px.violin(
            df,
            x='Source_File',
            y='Updated Charlson',
            color='Charlson Risk',
            box=True,
            points='all',
            title='Распределение Charlson по файлам и зонам риска',
            labels={'Updated Charlson': 'Charlson (обн.)', 'Source_File': 'Файл'},
            color_discrete_map={
                '🟢 Низкий': '#28a745',
                '🟡 Средний': '#ffc107',
                '🟠 Высокий': '#fd7e14',
                '🔴 Очень высокий': '#dc3545'
            }
        )
        fig_violin.update_layout(height=500)
        charts['violin'] = fig_violin
    else:
        # Если один файл, показываем обычный violin
        fig_violin = px.violin(
            df,
            y='Updated Charlson',
            color='Charlson Risk',
            box=True,
            points='all',
            title='Распределение Charlson по зонам риска',
            labels={'Updated Charlson': 'Charlson (обн.)'},
            color_discrete_map={
                '🟢 Низкий': '#28a745',
                '🟡 Средний': '#ffc107',
                '🟠 Высокий': '#fd7e14',
                '🔴 Очень высокий': '#dc3545'
            }
        )
        fig_violin.update_layout(height=400)
        charts['violin'] = fig_violin
    
    # 3. Heatmap с возможностью выбора колонок
    # Создаём матрицу корреляции
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    corr_matrix = df[numeric_cols].corr()
    
    # Берём только колонки с коморбидностями
    comorbidity_cols = [col for col in CHARLSON_MAPPINGS.keys() if col in df.columns]
    if comorbidity_cols and len(comorbidity_cols) > 2:
        corr_subset = df[comorbidity_cols].corr()
        fig_corr = go.Figure(data=go.Heatmap(
            z=corr_subset.values,
            x=corr_subset.columns,
            y=corr_subset.index,
            colorscale='RdBu_r',
            zmin=-1,
            zmax=1,
            text=np.round(corr_subset.values, 2),
            texttemplate='%{text:.2f}',
            textfont={"size": 8},
            hovertemplate='%{x} ↔ %{y}<br>Корреляция: %{z:.2f}<extra></extra>'
        ))
        fig_corr.update_layout(
            title='Корреляционная матрица заболеваний (Charlson)',
            height=600,
            width=800,
            xaxis={'tickangle': 45, 'tickfont': {'size': 8}},
            yaxis={'tickfont': {'size': 8}},
            margin=dict(l=50, r=50, t=80, b=200)
        )
        charts['correlation'] = fig_corr
    
    # 4. Распределение с возможностью выбора
    charts['distribution'] = None
    
    return charts


def create_radar_chart(df, patient_id):
    """
    Создаёт радарную диаграмму для конкретного пациента.
    """
    patient_data = df[df['Patient_ID'] == patient_id]
    if patient_data.empty:
        return None
    
    # Берём категории Charlson
    categories = [col for col in CHARLSON_MAPPINGS.keys() if col in df.columns]
    values = [patient_data[col].values[0] for col in categories]
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=patient_id,
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
        title=f'Профиль коморбидности для пациента {patient_id}',
        height=500,
        width=700
    )
    
    return fig