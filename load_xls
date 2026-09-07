import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Анализ данных", layout="wide")

st.title("ߓʠАнализ данных из Excel")
st.markdown("---")

# Загрузка файла
uploaded_file = st.file_uploader(
    "Загрузите Excel файл",
    type=['xlsx', 'xls']
)

if uploaded_file is not None:
    try:
        # Чтение Excel файла
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        # Проверяем, что есть данные
        if df.empty:
            st.error("Файл пуст")
            st.stop()
        
        # Проверяем количество колонок
        if len(df.columns) < 2:
            st.error("Файл должен содержать минимум 2 колонки")
            st.stop()
        
        # Берем первые две колонки
        df = df.iloc[:, :2]
        df.columns = ['Название', 'Значение']
        
        # Преобразуем названия в строки
        df['Название'] = df['Название'].astype(str)
        
        # Преобразуем значения в числа
        df['Значение'] = pd.to_numeric(df['Значение'], errors='coerce')
        
        # Удаляем строки с NaN
        df = df.dropna(subset=['Значение'])
        
        if len(df) == 0:
            st.warning("Нет числовых данных для анализа")
        else:
            # Отображение данных
            st.subheader("Данные")
            st.dataframe(df, use_container_width=True, height=300)
            
            # Статистика
            st.subheader("Статистика")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Количество", len(df))
            with col2:
                st.metric("Сумма", f"{df['Значение'].sum():.2f}")
            with col3:
                st.metric("Среднее", f"{df['Значение'].mean():.2f}")
            with col4:
                st.metric("Размах", f"{df['Значение'].max() - df['Значение'].min():.2f}")
            
            # Детальная статистика
            st.subheader("Детальная статистика")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"Минимальное значение: {df['Значение'].min():.2f}")
                st.info(f"Максимальное значение: {df['Значение'].max():.2f}")
                st.info(f"Сумма всех значений: {df['Значение'].sum():.2f}")
                st.info(f"Среднее значение: {df['Значение'].mean():.2f}")
            
            with col2:
                st.info(f"Медиана: {df['Значение'].median():.2f}")
                st.info(f"Стандартное отклонение: {df['Значение'].std():.2f}")
                st.info(f"Дисперсия: {df['Значение'].var():.2f}")
                st.info(f"Уникальных названий: {df['Название'].nunique()}")
            
            # Визуализация
            st.subheader("Визуализация")
            
            tab1, tab2, tab3 = st.tabs(["Гистограмма", "График тренда", "Топ-5"])
            
            with tab1:
                fig = px.bar(df, x='Название', y='Значение', 
                           title='Значения по категориям',
                           color='Значение',
                           color_continuous_scale='Viridis',
                           height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                fig = px.line(df, x='Название', y='Значение',
                            title='Изменение значений',
                            markers=True,
                            height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                top5 = df.nlargest(5, 'Значение')
                fig = px.bar(top5, x='Название', y='Значение',
                           title='Топ-5 максимальных значений',
                           color='Значение',
                           color_continuous_scale='Reds',
                           height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            # Дополнительная информация
            with st.expander("Полная статистика"):
                st.subheader("Статистика по колонке 'Значение'")
                st.dataframe(df['Значение'].describe())
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Топ-3 максимальных")
                    st.dataframe(df.nlargest(3, 'Значение'))
                with col2:
                    st.subheader("Топ-3 минимальных")
                    st.dataframe(df.nsmallest(3, 'Значение'))
                
                st.subheader("Экспорт результатов")
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="Скачать результаты (CSV)",
                    data=csv,
                    file_name='analyzed_data.csv',
                    mime='text/csv'
                )
            
    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {str(e)}")
else:
    st.info("Загрузите Excel файл для начала анализа")
    st.markdown("""
    ### Требования к файлу:
    - Формат: .xlsx или .xls
    - Минимум 2 колонки
    - Первая колонка - названия (текст)
    - Вторая колонка - значения (числа)
    
    ### Пример:
    | Название | Значение |
    |----------|----------|
    | Товар 1  | 150      |
    | Товар 2  | 230      |
    | Товар 3  | 180      |
    | Товар 4  | 95       |
    | Товар 5  | 310      |
    """)
