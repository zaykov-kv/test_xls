import streamlit as st
import pandas as pd
from datetime import datetime
import zoneinfo


def get_local_timezone():
    """Определяет локальный часовой пояс компьютера."""
    try:
        local_tz = datetime.now().astimezone().tzinfo
        if local_tz:
            return local_tz
    except:
        pass
    
    try:
        return zoneinfo.ZoneInfo('localtime')
    except:
        pass
    
    return zoneinfo.ZoneInfo('UTC')


def format_datetime(dt):
    """Преобразует datetime в локальный часовой пояс и форматирует."""
    if dt is None:
        return ""
    try:
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
        
        local_tz = get_local_timezone()
        
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC')
        
        dt_local = dt.tz_convert(local_tz)
        return dt_local.strftime('%d.%m.%Y %H:%M')
    except:
        return str(dt)


def normalize_column_names(df):
    """
    Приводит названия колонок из формата базы данных к формату приложения.
    """
    if df is None or df.empty:
        return df
    
    rename_map = {}
    
    # Основные колонки
    if 'source_file' in df.columns and 'Source_File' not in df.columns:
        rename_map['source_file'] = 'Source_File'
    if 'patient_id_text' in df.columns and 'Patient_ID' not in df.columns:
        rename_map['patient_id_text'] = 'Patient_ID'
    if 'icd_codes' in df.columns and 'ICD_codes' not in df.columns:
        rename_map['icd_codes'] = 'ICD_codes'
    if 'charlson_risk' in df.columns and 'Charlson Risk' not in df.columns:
        rename_map['charlson_risk'] = 'Charlson Risk'
    if 'elixhauser_risk' in df.columns and 'Elixhauser Risk' not in df.columns:
        rename_map['elixhauser_risk'] = 'Elixhauser Risk'
    if 'updated_charlson' in df.columns and 'Updated Charlson' not in df.columns:
        rename_map['updated_charlson'] = 'Updated Charlson'
    if 'van_walraven_elixhauser' in df.columns and 'van Walraven Elixhauser' not in df.columns:
        rename_map['van_walraven_elixhauser'] = 'van Walraven Elixhauser'
    if 'original_charlson' in df.columns and 'Original Charlson' not in df.columns:
        rename_map['original_charlson'] = 'Original Charlson'
    if 'ahrq_elixhauser' in df.columns and 'AHRQ Elixhauser' not in df.columns:
        rename_map['ahrq_elixhauser'] = 'AHRQ Elixhauser'
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    return df