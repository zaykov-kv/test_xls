"""
Подключение к Supabase и базовые операции.
"""

import streamlit as st
import pandas as pd
import json
import io
from supabase import create_client, Client
from typing import Optional


def get_supabase_config():
    """Получает конфигурацию Supabase из секретов."""
    try:
        url = st.secrets.get("SUPABASE_URL", "").strip()
        key = st.secrets.get("SUPABASE_KEY", "").strip()
    except:
        url = ""
        key = ""
    
    if not url:
        url = "https://your-project.supabase.co"
        st.warning("⚠️ SUPABASE_URL не найден в секретах. Используется значение по умолчанию.")
    
    if not key:
        key = "your-anon-key"
        st.warning("⚠️ SUPABASE_KEY не найден в секретах. Используется значение по умолчанию.")
    
    if url and not url.startswith("https://") and not url.startswith("http://"):
        url = "https://" + url
    
    return url, key


def create_supabase_client() -> Optional[Client]:
    """Создаёт и возвращает клиент Supabase."""
    url, key = get_supabase_config()
    
    if not url or not key:
        st.error("❌ Секреты Supabase не найдены.")
        return None
    
    try:
        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"❌ Ошибка подключения к Supabase: {str(e)}")
        return None