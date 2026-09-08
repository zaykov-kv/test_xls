# icd_parser.py
import re
import pandas as pd
from typing import List, Set

def parse_icd_codes(text: str) -> Set[str]:
    """
    Извлекает все коды МКБ-10 из строки.
    
    Args:
        text: Строка с кодами (например: "I21, E11.9, C50")
    
    Returns:
        Множество найденных кодов в верхнем регистре
    """
    if not text or pd.isna(text):
        return set()
    
    # Находит паттерны: буква + цифра + (цифра/точка/цифра)
    codes = re.findall(r'[A-Za-z][0-9][0-9]?\.?[0-9]?', str(text))
    return {code.upper() for code in codes}

def normalize_code(code: str) -> str:
    """Удаляет точку из кода для сравнения (E11.9 → E119)"""
    return code.replace('.', '')

def has_condition(patient_codes: Set[str], condition_codes: List[str]) -> int:
    """
    Проверяет, есть ли у пациента хотя бы один код из списка.
    
    Args:
        patient_codes: Множество кодов пациента
        condition_codes: Список кодов для конкретного заболевания
    
    Returns:
        1 - если есть совпадение, 0 - если нет
    """
    patient_norm = {normalize_code(c) for c in patient_codes}
    condition_norm = {normalize_code(c) for c in condition_codes}
    
    # Проверяем точное совпадение
    if patient_norm & condition_norm:
        return 1
    
    # Проверяем совпадение по первым символам (для кодов с разной детализацией)
    for pc in patient_norm:
        for cc in condition_norm:
            if pc.startswith(cc) or cc.startswith(pc):
                return 1
    
    return 0