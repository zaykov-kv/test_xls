import streamlit as st
import pandas as pd


def render_raw_data(all_results, combined_df):
    """Отображает исходные данные с возможностью редактирования."""
    with st.expander("📋 Редактирование исходных данных", expanded=False):
        st.markdown("**✏️ Редактирование данных пациентов**")
        st.caption("💡 Вы можете редактировать ID пациента и коды МКБ-10. После сохранения данные будут пересчитаны автоматически.")
        
        if not all_results:
            st.warning("Нет данных для редактирования")
            return combined_df
        
        if combined_df is None or combined_df.empty:
            st.warning("Нет данных для редактирования")
            return combined_df
        
        combined_df = combined_df.copy()
        if 'Patient_ID' in combined_df.columns:
            combined_df['Patient_ID'] = combined_df['Patient_ID'].astype(str)
        if 'ICD_codes' in combined_df.columns:
            combined_df['ICD_codes'] = combined_df['ICD_codes'].astype(str)
        if 'Source_File' in combined_df.columns:
            combined_df['Source_File'] = combined_df['Source_File'].astype(str)
        
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
            file_df = all_results[selected_file].copy()
            
            # Приводим колонки к единому формату
            if 'Source_File' not in file_df.columns:
                if 'source_file' in file_df.columns:
                    file_df['Source_File'] = file_df['source_file']
                else:
                    file_df['Source_File'] = selected_file
            
            if 'Patient_ID' not in file_df.columns:
                if 'patient_id_text' in file_df.columns:
                    file_df['Patient_ID'] = file_df['patient_id_text']
                elif 'patient_id' in file_df.columns:
                    file_df['Patient_ID'] = file_df['patient_id']
                else:
                    file_df['Patient_ID'] = ""
            
            if 'ICD_codes' not in file_df.columns:
                if 'icd_codes' in file_df.columns:
                    file_df['ICD_codes'] = file_df['icd_codes']
                else:
                    file_df['ICD_codes'] = ""
            
            if 'Patient_ID' in file_df.columns:
                file_df['Patient_ID'] = file_df['Patient_ID'].astype(str)
            if 'ICD_codes' in file_df.columns:
                file_df['ICD_codes'] = file_df['ICD_codes'].astype(str)
            
            display_cols = []
            if 'Source_File' in file_df.columns:
                display_cols.append('Source_File')
            if 'Patient_ID' in file_df.columns:
                display_cols.append('Patient_ID')
            if 'ICD_codes' in file_df.columns:
                display_cols.append('ICD_codes')
            
            if not display_cols:
                file_df['Source_File'] = selected_file
                file_df['Patient_ID'] = file_df.index.astype(str)
                file_df['ICD_codes'] = ""
                display_cols = ['Source_File', 'Patient_ID', 'ICD_codes']
            
            edit_df = file_df[display_cols].copy()
            
            show_n = st.selectbox(
                "Показывать записей:",
                options=[5, 10, 20, 50, 100, 0],
                format_func=lambda x: "Все" if x == 0 else str(x),
                index=1,
                key="edit_show_n"
            )
            
            st.markdown(f"**Редактирование файла: {selected_file}**")
            
            display_df = edit_df.copy() if show_n == 0 else edit_df.head(show_n).copy()
            
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
                        help="Введите коды через разделители",
                        required=True
                    )
                }
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("💾 Сохранить и пересчитать", use_container_width=True, type="primary"):
                    try:
                        for idx, row in edited_df.iterrows():
                            patient_id = row.get('Patient_ID', '')
                            icd_codes = row.get('ICD_codes', '')
                            
                            if pd.isna(patient_id) or str(patient_id).strip() == '':
                                continue
                            
                            if 'Patient_ID' in file_df.columns:
                                mask = (file_df['Patient_ID'].astype(str) == str(patient_id))
                                if 'Source_File' in file_df.columns:
                                    mask = mask & (file_df['Source_File'] == selected_file)
                                
                                if mask.any():
                                    file_df.loc[mask, 'ICD_codes'] = icd_codes
                                else:
                                    new_row = {col: 0 for col in file_df.columns}
                                    if 'Source_File' in new_row:
                                        new_row['Source_File'] = selected_file
                                    if 'Patient_ID' in new_row:
                                        new_row['Patient_ID'] = str(patient_id)
                                    if 'ICD_codes' in new_row:
                                        new_row['ICD_codes'] = icd_codes
                                    file_df = pd.concat([file_df, pd.DataFrame([new_row])], ignore_index=True)
                        
                        all_results[selected_file] = file_df
                        
                        with st.spinner("⏳ Пересчёт данных..."):
                            from analysis import calculate_patients, add_risk_zones
                            
                            calc_df = file_df[['Patient_ID', 'ICD_codes']].copy()
                            new_results = calculate_patients(calc_df, selected_file)
                            new_result_df = pd.DataFrame(new_results)
                            new_result_df = add_risk_zones(new_result_df)
                            
                            all_results[selected_file] = new_result_df
                            
                            updated_combined = []
                            for fname, fdf in all_results.items():
                                updated_combined.append(fdf)
                            if updated_combined:
                                new_combined = pd.concat(updated_combined, ignore_index=True)
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
                preview_cols = [col for col in ['Patient_ID', 'ICD_codes'] if col in file_df.columns]
                if preview_cols:
                    st.dataframe(file_df[preview_cols].head(10), use_container_width=True)
                    if len(file_df) > 10:
                        st.caption(f"Показано 10 из {len(file_df)} записей")
    
    if 'combined_df' in st.session_state:
        return st.session_state['combined_df']
    
    return combined_df