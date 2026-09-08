import requests
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional

# --- NLM API (БЕЗ АВТОРИЗАЦИИ) ---
NLM_API_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"


@st.cache_data(ttl=3600)
def get_icd10_code_details(code: str) -> Optional[Dict]:
    """
    Получение описания по точному коду МКБ-10 через NLM API.
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
                "code": display_data[0][1],
                "description": display_data[0][0]
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
                    "code": display_data[0][1],
                    "description": display_data[0][0]
                }

        return None

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Ошибка запроса к NLM API: {str(e)}")
        return None


def validate_icd10_codes(codes_text: str) -> Dict:
    """
    Проверяет список кодов МКБ-10 через NLM API.
    """
    from icd_parser import parse_icd_codes

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