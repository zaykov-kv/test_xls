import streamlit as st
import pandas as pd
from datetime import datetime
from database_supabase import SupabaseManager
from visualizations.utils import format_datetime


def render_database_interface():
    """Отображает интерфейс для работы с базой данных."""
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
        
        # --- Вкладка 2: Загрузка ---
        with tab2:
            st.markdown("**Загрузить ранее сохранённые данные**")
            
            with st.spinner("⏳ Загрузка списка сессий..."):
                sessions = db.get_sessions(limit=20)
            
            if sessions.empty:
                st.warning("Нет сохранённых сессий в базе данных")
                st.info("💡 Сначала сохраните данные через вкладку 'Сохранить текущие данные'")
            else:
                if 'created_at' in sessions.columns:
                    sessions['created_at_display'] = sessions['created_at'].apply(format_datetime)
                
                session_options = {}
                for _, row in sessions.iterrows():
                    display_name = f"{row['session_id']} - {row['file_name']} ({row.get('created_at_display', row.get('created_at', ''))})"
                    session_options[display_name] = row['session_id']
                
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
                
                with st.expander("📋 Список всех сессий"):
                    st.dataframe(
                        sessions[['session_id', 'created_at', 'file_name', 'total_patients', 'avg_charlson']],
                        use_container_width=True,
                        hide_index=True
                    )
        
        # --- Вкладка 3: История сессий ---
        with tab3:
            st.markdown("**📊 История сессий**")
            
            limit = st.slider("Количество сессий для отображения:", 5, 100, 20, key="history_limit")
            sessions = db.get_sessions(limit=limit)
            
            if sessions.empty:
                st.info("Нет сохранённых сессий")
            else:
                if 'created_at' in sessions.columns:
                    sessions['created_at_display'] = sessions['created_at'].apply(format_datetime)
                
                st.dataframe(
                    sessions,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "session_id": "ID",
                        "created_at_display": "Дата создания",
                        "file_name": "Название",
                        "total_patients": "Пациентов",
                        "avg_charlson": "Ср. Charlson"
                    }
                )
                
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Всего сессий", len(sessions))
                with col2:
                    st.metric("Всего пациентов", sessions['total_patients'].sum())
                with col3:
                    st.metric("Ср. пациентов на сессию", f"{sessions['total_patients'].mean():.1f}")
        
        # --- Вкладка 4: Поиск пациентов ---
        with tab4:
            st.markdown("**🔍 Поиск пациентов**")
            st.caption("💡 Поиск по ID пациента, кодам МКБ-10 или другим данным")
            
            search_term = st.text_input(
                "Введите текст для поиска:",
                placeholder="Например: E11.9, 001, диабет",
                key="db_search_term"
            )
            
            if search_term and len(search_term.strip()) >= 2:
                with st.spinner("⏳ Поиск..."):
                    results = db.search_patients(search_term)
                    
                    if results.empty:
                        st.info("Ничего не найдено. Попробуйте изменить запрос.")
                        st.caption("💡 Подсказка: ищите по ID пациента или по коду МКБ-10 (например, E11.9)")
                    else:
                        st.success(f"✅ Найдено {len(results)} записей")
                        
                        if 'session_date' in results.columns:
                            results['session_date'] = pd.to_datetime(results['session_date'])
                            results['session_date'] = results['session_date'].dt.strftime('%d.%m.%Y %H:%M')
                        
                        st.dataframe(
                            results,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "patient_id_text": "ID пациента",
                                "source_file": "Файл",
                                "icd_codes": "Коды МКБ-10",
                                "updated_charlson": "Charlson",
                                "charlson_risk": "Риск C",
                                "van_walraven_elixhauser": "Elixhauser",
                                "elixhauser_risk": "Риск E",
                                "session_name": "Сессия",
                                "session_date": "Дата"
                            }
                        )
                        
                        # Кнопка для загрузки найденных пациентов
                        if st.button("📂 Загрузить всех найденных пациентов", use_container_width=True):
                            with st.spinner("⏳ Загрузка полных данных пациентов..."):
                                full_data_list = []
                                session_ids = results['session_id'].unique()
                                
                                for session_id in session_ids:
                                    full_session_data = db.get_session_data(session_id)
                                    if full_session_data is not None and not full_session_data.empty:
                                        patient_ids = results[results['session_id'] == session_id]['patient_id_text'].tolist()
                                        filtered_patients = full_session_data[full_session_data['Patient_ID'].isin(patient_ids)]
                                        full_data_list.append(filtered_patients)
                                
                                if full_data_list:
                                    combined_full_data = pd.concat(full_data_list, ignore_index=True)
                                    st.session_state.combined_df = combined_full_data
                                    st.session_state.all_results = {'search_results': combined_full_data}
                                    st.session_state.data_source = 'database'
                                    st.session_state.uploaded_files_processed = True
                                    st.success(f"✅ Загружено {len(combined_full_data)} пациентов из поиска с полными данными")
                                    st.rerun()
                                else:
                                    st.error("❌ Не удалось загрузить полные данные пациентов")
            elif search_term and len(search_term.strip()) < 2:
                st.info("💡 Введите минимум 2 символа для поиска")