import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
import json
from typing import Optional, List, Dict
import io


class DatabaseManager:
    """
    Класс для управления базой данных SQLite.
    """
    
    def __init__(self, db_path: str = "comorbidity.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self):
        """Создаёт и возвращает соединение с БД."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Инициализирует таблицы в базе данных."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица для хранения сессий (загруженные файлы)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_name TEXT,
                    total_patients INTEGER,
                    avg_charlson REAL,
                    avg_elixhauser REAL,
                    data_json TEXT
                )
            ''')
            
            # Таблица для хранения отдельных пациентов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    source_file TEXT,
                    patient_id_text TEXT,
                    icd_codes TEXT,
                    updated_charlson REAL,
                    charlson_risk TEXT,
                    van_walraven_elixhauser REAL,
                    elixhauser_risk TEXT,
                    full_data_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы для быстрого поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_session ON patients(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_id ON patients(patient_id_text)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(created_at)')
            
            conn.commit()
    
    def save_session(self, df: pd.DataFrame, file_name: str = "uploaded_data") -> int:
        """
        Сохраняет сессию с данными в базу данных.
        
        Args:
            df: DataFrame с результатами
            file_name: Имя файла или описание сессии
        
        Returns:
            ID сохранённой сессии
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Рассчитываем статистику
            total_patients = len(df)
            avg_charlson = df['Updated Charlson'].mean() if not df.empty else 0
            avg_elixhauser = df['van Walraven Elixhauser'].mean() if not df.empty else 0
            
            # Сохраняем полные данные как JSON
            data_json = df.to_json(orient='records', date_format='iso')
            
            # Вставляем сессию
            cursor.execute('''
                INSERT INTO sessions (file_name, total_patients, avg_charlson, avg_elixhauser, data_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (file_name, total_patients, avg_charlson, avg_elixhauser, data_json))
            
            session_id = cursor.lastrowid
            
            # Сохраняем каждого пациента
            for _, row in df.iterrows():
                # Получаем полные данные пациента как JSON
                full_data = row.to_dict()
                full_data_json = json.dumps(full_data, default=str)
                
                cursor.execute('''
                    INSERT INTO patients (
                        session_id, source_file, patient_id_text, icd_codes,
                        updated_charlson, charlson_risk,
                        van_walraven_elixhauser, elixhauser_risk,
                        full_data_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    row.get('Source_File', ''),
                    row.get('Patient_ID', ''),
                    row.get('ICD_codes', ''),
                    row.get('Updated Charlson', 0),
                    row.get('Charlson Risk', ''),
                    row.get('van Walraven Elixhauser', 0),
                    row.get('Elixhauser Risk', ''),
                    full_data_json
                ))
            
            conn.commit()
            return session_id
    
    def get_sessions(self, limit: int = 50) -> pd.DataFrame:
        """
        Возвращает список сохранённых сессий.
        """
        with self._get_connection() as conn:
            query = f'''
                SELECT 
                    session_id,
                    created_at,
                    file_name,
                    total_patients,
                    avg_charlson,
                    avg_elixhauser
                FROM sessions
                ORDER BY created_at DESC
                LIMIT {limit}
            '''
            return pd.read_sql_query(query, conn)
    
    def get_session_data(self, session_id: int) -> Optional[pd.DataFrame]:
        """
        Возвращает данные конкретной сессии.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем данные сессии
            cursor.execute('SELECT data_json FROM sessions WHERE session_id = ?', (session_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                try:
                    # Используем StringIO для чтения JSON из строки
                    json_data = result[0]
                    df = pd.read_json(io.StringIO(json_data), orient='records')
                    return df
                except Exception as e:
                    print(f"Ошибка при загрузке данных: {e}")
                    return None
            
            return None
    
    def get_session_patients(self, session_id: int) -> pd.DataFrame:
        """
        Возвращает список пациентов из конкретной сессии.
        """
        with self._get_connection() as conn:
            query = '''
                SELECT 
                    patient_id,
                    source_file,
                    patient_id_text,
                    icd_codes,
                    updated_charlson,
                    charlson_risk,
                    van_walraven_elixhauser,
                    elixhauser_risk,
                    created_at
                FROM patients
                WHERE session_id = ?
                ORDER BY patient_id_text
            '''
            return pd.read_sql_query(query, conn, params=(session_id,))
    
    def delete_session(self, session_id: int) -> bool:
        """
        Удаляет сессию и всех её пациентов.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Удаляем пациентов (каскадно)
            cursor.execute('DELETE FROM patients WHERE session_id = ?', (session_id,))
            # Удаляем сессию
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def search_patients(self, search_term: str) -> pd.DataFrame:
        """
        Поиск пациентов по ID или кодам МКБ-10.
        """
        with self._get_connection() as conn:
            query = '''
                SELECT 
                    p.patient_id,
                    p.source_file,
                    p.patient_id_text,
                    p.icd_codes,
                    p.updated_charlson,
                    p.charlson_risk,
                    p.van_walraven_elixhauser,
                    p.elixhauser_risk,
                    s.file_name as session_name,
                    s.created_at as session_date
                FROM patients p
                JOIN sessions s ON p.session_id = s.session_id
                WHERE 
                    p.patient_id_text LIKE ? OR 
                    p.icd_codes LIKE ? OR
                    p.full_data_json LIKE ?
                ORDER BY s.created_at DESC
                LIMIT 100
            '''
            search_pattern = f'%{search_term}%'
            return pd.read_sql_query(
                query, 
                conn, 
                params=(search_pattern, search_pattern, search_pattern)
            )