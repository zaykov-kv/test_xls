import streamlit as st
import pandas as pd
from datetime import datetime
import json
from typing import Optional, List, Dict
from supabase import create_client, Client
import io
import socket

# --- ПОДКЛЮЧЕНИЕ К SUPABASE ---
def get_supabase_config():
    """Получает конфигурацию Supabase из секретов с диагностикой."""
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip()
        key = st.secrets.get("SUPABASE_KEY", "").strip()
    except:
        url = ""
        key = ""
    
    # Если URL пустой, пробуем стандартный
    if not url:
        url = "https://your-project.supabase.co"
        st.warning("⚠️ SUPABASE_URL не найден в секретах. Используется значение по умолчанию.")
    
    if not key:
        key = "your-anon-key"
        st.warning("⚠️ SUPABASE_KEY не найден в секретах. Используется значение по умолчанию.")
    
    # Добавляем https:// если нужно
    if url and not url.startswith("https://") and not url.startswith("http://"):
        url = "https://" + url
    
    return url, key


class SupabaseManager:
    """
    Класс для управления базой данных Supabase.
    """
    
    def __init__(self):
        self.client = None
        self.connected = False
        
        # Получаем конфигурацию
        url, key = get_supabase_config()
        
        if not url or not key:
            st.error("❌ Секреты Supabase не найдены. Проверьте файл .streamlit/secrets.toml")
            return
        
        # Проверяем доступность хоста
        try:
            host = url.replace("https://", "").replace("http://", "").split("/")[0]
            socket.gethostbyname(host)
        except socket.gaierror as e:
            st.error(f"❌ Не удалось найти хост {host}. Проверьте подключение к интернету.")
            return
        except Exception as e:
            st.error(f"❌ Ошибка при проверке хоста: {str(e)}")
            return
        
        # Подключаемся к Supabase
        try:
            self.client: Client = create_client(url, key)
            self.connected = True
            # st.success("✅ Подключение к Supabase установлено")
        except Exception as e:
            st.error(f"❌ Ошибка подключения к Supabase: {str(e)}")
            self.client = None
    
    def save_session(self, df: pd.DataFrame, file_name: str = "uploaded_data") -> Optional[int]:
        """
        Сохраняет сессию с данными в Supabase.
        """
        if self.client is None:
            st.error("❌ Нет подключения к Supabase")
            return None
        
        try:
            total_patients = len(df)
            avg_charlson = df['Updated Charlson'].mean() if not df.empty else 0
            avg_elixhauser = df['van Walraven Elixhauser'].mean() if not df.empty else 0
            
            data_json = df.to_json(orient='records', date_format='iso')
            
            session_data = {
                'file_name': file_name,
                'total_patients': total_patients,
                'avg_charlson': float(avg_charlson),
                'avg_elixhauser': float(avg_elixhauser),
                'data_json': data_json
            }
            
            result = self.client.table('sessions').insert(session_data).execute()
            
            if not result.data:
                st.error("❌ Нет данных в ответе от Supabase")
                return None
            
            session_id = result.data[0]['session_id']
            
            patients_data = []
            for _, row in df.iterrows():
                full_data = row.to_dict()
                full_data_json = json.dumps(full_data, default=str)
                
                patients_data.append({
                    'session_id': session_id,
                    'source_file': str(row.get('Source_File', '')),
                    'patient_id_text': str(row.get('Patient_ID', '')),
                    'icd_codes': str(row.get('ICD_codes', '')),
                    'updated_charlson': float(row.get('Updated Charlson', 0)),
                    'charlson_risk': str(row.get('Charlson Risk', '')),
                    'van_walraven_elixhauser': float(row.get('van Walraven Elixhauser', 0)),
                    'elixhauser_risk': str(row.get('Elixhauser Risk', '')),
                    'full_data_json': full_data_json
                })
            
            if patients_data:
                self.client.table('patients').insert(patients_data).execute()
            
            return session_id
            
        except Exception as e:
            st.error(f"❌ Ошибка при сохранении: {str(e)}")
            return None
    
    def get_sessions(self, limit: int = 50) -> pd.DataFrame:
        """
        Возвращает список сохранённых сессий.
        """
        if self.client is None:
            st.warning("⚠️ Нет подключения к Supabase")
            return pd.DataFrame()
        
        try:
            result = self.client.table('sessions')\
                .select('session_id, created_at, file_name, total_patients, avg_charlson, avg_elixhauser')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                return pd.DataFrame(result.data)
            return pd.DataFrame()
                
        except Exception as e:
            st.error(f"❌ Ошибка при загрузке сессий: {str(e)}")
            return pd.DataFrame()
    
    def get_session_data(self, session_id: int) -> Optional[pd.DataFrame]:
        """
        Возвращает данные конкретной сессии с приведением типов.
        """
        if self.client is None:
            st.warning("⚠️ Нет подключения к Supabase")
            return None
        
        try:
            result = self.client.table('sessions')\
                .select('data_json')\
                .eq('session_id', session_id)\
                .execute()
            
            if result.data and result.data[0].get('data_json'):
                try:
                    json_data = result.data[0]['data_json']
                    df = pd.read_json(io.StringIO(json_data), orient='records')
                    
                    # Приводим типы для совместимости
                    text_columns = ['Patient_ID', 'ICD_codes', 'Source_File', 'Charlson Risk', 'Elixhauser Risk']
                    for col in text_columns:
                        if col in df.columns:
                            df[col] = df[col].astype(str)
                    
                    numeric_columns = ['Updated Charlson', 'Original Charlson', 'AHRQ Elixhauser', 'van Walraven Elixhauser']
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    return df
                    
                except Exception as e:
                    st.error(f"❌ Ошибка при парсинге данных: {str(e)}")
                    return None
            
            return None
            
        except Exception as e:
            st.error(f"❌ Ошибка при загрузке данных сессии: {str(e)}")
            return None
    
    def get_session_patients(self, session_id: int) -> pd.DataFrame:
        """Возвращает список пациентов из конкретной сессии."""
        if self.client is None:
            return pd.DataFrame()
        
        try:
            result = self.client.table('patients')\
                .select('patient_id, source_file, patient_id_text, icd_codes, updated_charlson, charlson_risk, van_walraven_elixhauser, elixhauser_risk, created_at')\
                .eq('session_id', session_id)\
                .order('patient_id_text')\
                .execute()
            
            if result.data:
                return pd.DataFrame(result.data)
            return pd.DataFrame()
            
        except Exception as e:
            st.error(f"❌ Ошибка при загрузке пациентов: {str(e)}")
            return pd.DataFrame()
    
    def delete_session(self, session_id: int) -> bool:
        """Удаляет сессию и всех её пациентов."""
        if self.client is None:
            return False
        
        try:
            self.client.table('patients').delete().eq('session_id', session_id).execute()
            result = self.client.table('sessions').delete().eq('session_id', session_id).execute()
            return len(result.data) > 0
        except Exception as e:
            st.error(f"❌ Ошибка при удалении: {str(e)}")
            return False
    
    def search_patients(self, search_term: str) -> pd.DataFrame:
        """Поиск пациентов по ID или кодам МКБ-10."""
        if self.client is None:
            st.warning("⚠️ Нет подключения к Supabase")
            return pd.DataFrame()
        
        if not search_term or len(search_term.strip()) < 2:
            st.info("💡 Введите минимум 2 символа для поиска")
            return pd.DataFrame()
        
        try:
            search_pattern = f"%{search_term.strip()}%"
            
            # Пробуем через or_ с ilike
            result = self.client.table('patients')\
                .select('patient_id, source_file, patient_id_text, icd_codes, updated_charlson, charlson_risk, van_walraven_elixhauser, elixhauser_risk, created_at, session_id')\
                .or_(f"patient_id_text.ilike.{search_pattern}, icd_codes.ilike.{search_pattern}")\
                .limit(100)\
                .execute()
            
            # Если ничего не найдено, пробуем через текстовый поиск
            if not result.data:
                result = self.client.table('patients')\
                    .select('patient_id, source_file, patient_id_text, icd_codes, updated_charlson, charlson_risk, van_walraven_elixhauser, elixhauser_risk, created_at, session_id')\
                    .text_search('patient_id_text', search_term.strip())\
                    .limit(100)\
                    .execute()
            
            # Если всё ещё пусто, пробуем точное совпадение
            if not result.data:
                result = self.client.table('patients')\
                    .select('patient_id, source_file, patient_id_text, icd_codes, updated_charlson, charlson_risk, van_walraven_elixhauser, elixhauser_risk, created_at, session_id')\
                    .eq('patient_id_text', search_term.strip())\
                    .limit(100)\
                    .execute()
            
            # Если данные найдены, обрабатываем
            if result.data:
                df = pd.DataFrame(result.data)
                
                # Получаем информацию о сессиях
                if not df.empty and 'session_id' in df.columns:
                    session_ids = df['session_id'].unique().tolist()
                    if session_ids:
                        sessions = self.client.table('sessions')\
                            .select('session_id, file_name, created_at')\
                            .in_('session_id', session_ids)\
                            .execute()
                        
                        if sessions.data:
                            sessions_df = pd.DataFrame(sessions.data)
                            df = df.merge(sessions_df, on='session_id', how='left')
                            df = df.rename(columns={
                                'file_name': 'session_name',
                                'created_at_y': 'session_date'
                            })
                
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            st.error(f"❌ Ошибка при поиске: {str(e)}")
            return pd.DataFrame()