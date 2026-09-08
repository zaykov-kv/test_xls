import requests
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
import re
from datetime import datetime, timedelta
import html

# --- NLM API (БЕЗ АВТОРИЗАЦИИ) ---
# Документация: https://clinicaltables.nlm.nih.gov/apidoc/icd10cm/v3/doc.html
NLM_API_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"

# --- WHO ICD-API (С АВТОРИЗАЦИЕЙ) ---
TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
WHO_SEARCH_URL = "https://id.who.int/icd/entity/search"


class ICDTokenManager:
    """Управляет токеном для WHO ICD-API."""
    
    def __init__(self):
        self.token = None
        self.expires_at = None
    
    def get_token(self) -> Optional[str]:
        """Получает токен доступа к WHO API."""
        
        # Проверяем, не истёк ли токен
        if self.token and self.expires_at and datetime.now() < self.expires_at:
            return self.token
        
        try:
            client_id = st.secrets.get("WHO_CLIENT_ID", "")
            client_secret = st.secrets.get("WHO_CLIENT_SECRET", "")
            
            if not client_id or not client_secret:
                st.error("❌ WHO_CLIENT_ID или WHO_CLIENT_SECRET не найдены в секретах")
                return None
            
            payload = {
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': 'icdapi_access',
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(TOKEN_URL, data=payload, timeout=10, verify=False)
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            return self.token
            
        except Exception as e:
            st.error(f"❌ Ошибка получения токена: {str(e)}")
            return None


# Глобальный экземпляр менеджера токенов
token_manager = ICDTokenManager()


# ============================================================================
# 1. ПОИСК ПО КОДУ (NLM API, БЕЗ АВТОРИЗАЦИИ)
# ============================================================================

@st.cache_data(ttl=3600)
def get_icd10_code_details(code: str) -> Optional[Dict]:
    """
    Получение описания по точному коду МКБ-10 через NLM API.
    
    Args:
        code: Код МКБ-10 (например, "E11.9")
    
    Returns:
        Словарь с ключами 'code' и 'description' или None
    """
    if not code:
        return None

    code_clean = code.strip().upper()

    params = {
        "terms": code_clean,
        "maxList": 1,
        "df": "code,name"
    }

    try:
        response = requests.get(NLM_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Формат ответа: [total, codes_array, {}, display_array]
        # display_array: [ ["name1", "code1"], ["name2", "code2"], ... ]
        display_data = data[3] if len(data) > 3 else []

        if display_data and len(display_data[0]) >= 2:
            return {
                "code": display_data[0][0],
                "description": display_data[0][1]
            }

        # Если точное не найдено, пробуем без точки (E119 вместо E11.9)
        if '.' in code_clean:
            code_no_dot = code_clean.replace('.', '')
            params = {
                "terms": code_no_dot,
                "maxList": 1,
                "df": "code,name"
            }
            response = requests.get(NLM_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            display_data = data[3] if len(data) > 3 else []
            if display_data and len(display_data[0]) >= 2:
                return {
                    "code": display_data[0][0],
                    "description": display_data[0][1]
                }

        return None

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Ошибка запроса к NLM API: {str(e)}")
        return None


# ============================================================================
# 2. ПОИСК ПО НАЗВАНИЮ (WHO API, С АВТОРИЗАЦИЕЙ)
# ============================================================================

@st.cache_data(ttl=3600)
def search_icd10_by_name(search_term: str, max_results: int = 10) -> List[Dict]:
    """
    Поиск кодов МКБ-10 по названию через WHO API.
    
    Args:
        search_term: Название на английском (например, "diabetes")
        max_results: Максимальное количество результатов
    
    Returns:
        Список словарей с ключами 'id' (числовой идентификатор) и 'description'
    """
    if not search_term or len(search_term.strip()) < 2:
        return []
    
    token = token_manager.get_token()
    if not token:
        st.warning("⚠️ Не удалось получить токен для WHO API")
        return []
    
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Accept-Language': 'en',
            'API-Version': 'v2'
        }
        
        params = {
            "q": search_term.strip(),
            "maxResults": max_results
        }
        
        response = requests.get(WHO_SEARCH_URL, headers=headers, params=params, timeout=15, verify=False)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        if "destinationEntities" in data:
            for item in data["destinationEntities"]:
                # Получаем ID (числовой идентификатор)
                entity_id = item.get("id", "")
                if entity_id:
                    # Извлекаем число из ID
                    match = re.search(r'/(\d+)$', entity_id)
                    if match:
                        code = match.group(1)
                    else:
                        code = entity_id.split('/')[-1]
                else:
                    code = None
                
                # Получаем название и убираем HTML-теги
                title = item.get("title", "")
                if isinstance(title, dict):
                    description = title.get("@value", "")
                else:
                    description = str(title)
                
                # Убираем HTML-теги <em class='found'> и </em>
                description = re.sub(r'<[^>]+>', '', description)
                description = html.unescape(description)
                
                if code and description:
                    results.append({
                        "id": code,
                        "description": description
                    })
        
        return results[:max_results]
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Ошибка при поиске по названию: {str(e)}")
        return []


# ============================================================================
# 3. ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПРОВЕРКИ КОДОВ
# ============================================================================

def validate_icd10_codes(codes_text: str) -> Dict:
    """
    Проверяет список кодов МКБ-10 через NLM API.
    
    Args:
        codes_text: Строка с кодами (например, "E11.9, I10")
    
    Returns:
        Словарь с ключами 'valid' (список валидных кодов) и 'invalid' (список невалидных)
    """
    from core.icd_parser import parse_icd_codes

    codes = list(parse_icd_codes(codes_text))
    if not codes:
        return {"valid": [], "invalid": []}

    valid_codes = []
    invalid_codes = []

    for code in codes:
        details = get_icd10_code_details(code)
        if details:
            valid_codes.append({
                "code": code,
                "description": details.get("description", ""),
                "original": code
            })
        else:
            invalid_codes.append(code)

    return {
        "valid": valid_codes,
        "invalid": invalid_codes
    }


# ============================================================================
# ЭКСПОРТ
# ============================================================================

__all__ = [
    'get_icd10_code_details',
    'search_icd10_by_name',
    'validate_icd10_codes',
    'token_manager'
]