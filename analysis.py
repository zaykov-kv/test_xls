import pandas as pd
import streamlit as st
from charlson import evaluate_charlson, calculate_charlson_scores
from elixhauser import evaluate_elixhauser, calculate_elixhauser_scores
from utils import add_risk_zones


def process_uploaded_files(uploaded_files):
    all_results = {}
    combined_results = []
    
    total_files = len(uploaded_files)
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    for file_idx, uploaded_file in enumerate(uploaded_files):
        try:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            
            is_valid, error_msg = validate_file(df, uploaded_file.name)
            if not is_valid:
                st.warning(error_msg)
                continue
            
            df = prepare_dataframe(df)
            if df is None:
                st.warning(f"⚠️ В файле '{uploaded_file.name}' нет данных с кодами МКБ-10, пропускаем")
                continue
            
            progress_text.text(f"⏳ Обработка файла: {uploaded_file.name} ({file_idx + 1}/{total_files})")
            results = calculate_patients(df, uploaded_file.name)
            
            result_df = pd.DataFrame(results)
            result_df = add_risk_zones(result_df)
            
            all_results[uploaded_file.name] = result_df
            combined_results.append(result_df)
            
            progress_bar.progress((file_idx + 1) / total_files)
            
        except Exception as e:
            st.error(f"❌ Ошибка при обработке файла '{uploaded_file.name}': {str(e)}")
            continue
    
    progress_text.empty()
    progress_bar.empty()
    
    return all_results, combined_results


def validate_file(df, filename):
    if df.empty:
        return False, f"⚠️ Файл '{filename}' пуст, пропускаем"
    if len(df.columns) < 2:
        return False, f"⚠️ Файл '{filename}' содержит менее 2 колонок, пропускаем"
    return True, "OK"


def prepare_dataframe(df):
    df = df.iloc[:, :2]
    df.columns = ['Patient_ID', 'ICD_codes']
    df['Patient_ID'] = df['Patient_ID'].astype(str)
    df['ICD_codes'] = df['ICD_codes'].astype(str)
    
    if df['ICD_codes'].str.strip().eq('').all():
        return None
    return df


def calculate_patients(df, source_file):
    results = []
    for _, row in df.iterrows():
        icd_codes = row['ICD_codes']
        
        charlson_cats = evaluate_charlson(icd_codes)
        charlson_scores = calculate_charlson_scores(charlson_cats)
        
        elixhauser_cats = evaluate_elixhauser(icd_codes)
        elixhauser_scores = calculate_elixhauser_scores(elixhauser_cats)
        
        results.append({
            'Source_File': source_file,
            'Patient_ID': row['Patient_ID'],
            'ICD_codes': icd_codes,
            **charlson_cats,
            **charlson_scores,
            **elixhauser_cats,
            **elixhauser_scores
        })
    
    return results


def get_file_summary(all_results):
    file_info = []
    for filename, df in all_results.items():
        file_info.append({
            'Файл': filename,
            'Пациентов': len(df),
            'Средний Charlson': df['Updated Charlson'].mean(),
            'Средний Elixhauser': df['van Walraven Elixhauser'].mean()
        })
    return pd.DataFrame(file_info)


def get_comparison_stats(filtered_df):
    comparison_df = filtered_df.groupby('Source_File').agg({
        'Patient_ID': 'count',
        'Updated Charlson': ['mean', 'median', 'min', 'max'],
        'van Walraven Elixhauser': ['mean', 'median', 'min', 'max']
    }).round(2)
    
    comparison_df.columns = [
        'Пациентов', 'Ср. Charlson', 'Мед. Charlson', 
        'Мин. Charlson', 'Макс. Charlson',
        'Ср. Elixhauser', 'Мед. Elixhauser', 
        'Мин. Elixhauser', 'Макс. Elixhauser'
    ]
    return comparison_df