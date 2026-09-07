# test_mappings.py - Тестовый справочник для отладки

import re
import pandas as pd
from typing import Dict, List, Tuple

# --- ТЕСТОВЫЙ СПРАВОЧНИК МКБ-10 ---
# Содержит 6 категорий из индекса Charlson для демонстрации

CHARLSON_MAPPINGS: Dict[str, List[str]] = {
    # 1. Инфаркт миокарда (вес 1)
    'Myocardial infarction': [
        'I21', 'I21.0', 'I21.1', 'I21.2', 'I21.3', 'I21.4', 'I21.9', 
        'I22', 'I22.0', 'I22.1', 'I22.8', 'I22.9', 'I25.2'
    ],
    
    # 2. Застойная сердечная недостаточность (вес 1)
    'Congestive heart failure': [
        'I09.9', 'I11.0', 'I13.0', 'I13.2', 'I25.5', 'I42.0', 'I42.5',
        'I42.6', 'I42.7', 'I42.8', 'I42.9', 'I43', 'I50', 'I50.0',
        'I50.1', 'I50.9', 'P29.0'
    ],
    
    # 3. Цереброваскулярные заболевания (инсульт) (вес 1)
    'Cerebrovascular disease': [
        'G45', 'G45.0', 'G45.1', 'G45.2', 'G45.3', 'G45.8', 'G45.9',
        'G46', 'H34.0', 'I60', 'I61', 'I62', 'I63', 'I64', 'I65',
        'I66', 'I67', 'I68', 'I69'
    ],
    
    # 4. Диабет без осложнений (вес 1)
    'Diabetes without complications': [
        'E10.0', 'E10.1', 'E10.9', 'E11.0', 'E11.1', 'E11.9',
        'E12.0', 'E12.1', 'E12.9', 'E13.0', 'E13.1', 'E13.9',
        'E14.0', 'E14.1', 'E14.9'
    ],
    
    # 5. Диабет с осложнениями (вес 2)
    'Diabetes with complications': [
        'E10.2', 'E10.3', 'E10.4', 'E10.5', 'E10.6', 'E10.7', 'E10.8',
        'E11.2', 'E11.3', 'E11.4', 'E11.5', 'E11.6', 'E11.7', 'E11.8',
        'E12.2', 'E12.3', 'E12.4', 'E12.5', 'E12.6', 'E12.7', 'E12.8',
        'E13.2', 'E13.3', 'E13.4', 'E13.5', 'E13.6', 'E13.7', 'E13.8',
        'E14.2', 'E14.3', 'E14.4', 'E14.5', 'E14.6', 'E14.7', 'E14.8'
    ],
    
    # 6. Злокачественное новообразование (рак) (вес 2)
    'Any malignancy': [
        'C00', 'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08',
        'C09', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17',
        'C18', 'C19', 'C20', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26',
        'C30', 'C31', 'C32', 'C33', 'C34', 'C37', 'C38', 'C39', 'C40',
        'C41', 'C43', 'C45', 'C46', 'C47', 'C48', 'C49', 'C50', 'C51',
        'C52', 'C53', 'C54', 'C55', 'C56', 'C57', 'C58', 'C60', 'C61',
        'C62', 'C63', 'C64', 'C65', 'C66', 'C67', 'C68', 'C69', 'C70',
        'C71', 'C72', 'C73', 'C74', 'C75', 'C76', 'C81', 'C82', 'C83',
        'C84', 'C85', 'C88', 'C90', 'C91', 'C92', 'C93', 'C94', 'C95',
        'C96', 'C97'
    ]
}

# --- ВЕСА ДЛЯ ИНДЕКСА CHARLSON (Quan et al. 2011) ---
# Для обновлённого индекса Charlson
CHARLSON_WEIGHTS: Dict[str, int] = {
    'Myocardial infarction': 0,
    'Congestive heart failure': 2,
    'Cerebrovascular disease': 0,
    'Diabetes without complications': 0,
    'Diabetes with complications': 1,
    'Any malignancy': 2
}

# --- ИЕРАРХИЯ (более тяжёлое состояние исключает лёгкое) ---
# Для индекса Charlson: диабет с осложнениями исключает диабет без осложнений
CHARLSON_HIERARCHY: List[Tuple[str, str]] = [
    ('Diabetes without complications', 'Diabetes with complications')
]

# ----------------------------------------------------------------------
# ФУНКЦИИ ДЛЯ РАБОТЫ СО СПРАВОЧНИКОМ
# ----------------------------------------------------------------------

def parse_icd_codes(text: str) -> List[str]:
    """
    Извлекает все коды МКБ-10 из строки.
    
    Args:
        text: Строка с кодами (например: "I21, E11.9, C50")
    
    Returns:
        Список найденных кодов в верхнем регистре
    """
    if pd.isna(text):
        return []
    # Находит все паттерны вида: буква(ы) + цифры(ы) + возможная точка + цифры
    codes = re.findall(r'[A-Za-z][0-9][0-9]?\.?[0-9]?', str(text))
    return [code.upper() for code in codes]

def check_condition(patient_codes: List[str], condition_codes: List[str]) -> int:
    """
    Проверяет, есть ли у пациента хотя бы один код из списка.
    
    Args:
        patient_codes: Список кодов МКБ-10 пациента
        condition_codes: Список кодов для конкретного заболевания
    
    Returns:
        1 - если есть совпадение, 0 - если нет
    """
    # Приводим коды к единому формату (без точки для сравнения)
    def normalize(code: str) -> str:
        return code.replace('.', '')
    
    patient_norm = [normalize(c) for c in patient_codes]
    condition_norm = [normalize(c) for c in condition_codes]
    
    for pc in patient_norm:
        for cc in condition_norm:
            # Проверяем точное совпадение или совпадение по первым символам
            if pc == cc or (len(cc) >= 3 and pc.startswith(cc)):
                return 1
    return 0

def evaluate_patient(
    patient_codes_text: str,
    mappings: Dict[str, List[str]],
    hierarchy: List[Tuple[str, str]]
) -> Dict[str, int]:
    """
    Оценивает пациента по всем категориям с учётом иерархии.
    
    Args:
        patient_codes_text: Строка с кодами МКБ-10
        mappings: Словарь {категория: [коды]}
        hierarchy: Список [(лёгкая_категория, тяжёлая_категория)]
    
    Returns:
        Словарь {категория: 0/1}
    """
    codes = parse_icd_codes(patient_codes_text)
    if not codes:
        return {cat: 0 for cat in mappings.keys()}
    
    # Первичная оценка
    results = {}
    for category, condition_codes in mappings.items():
        results[category] = check_condition(codes, condition_codes)
    
    # Применение иерархии
    for mild, severe in hierarchy:
        if results.get(severe, 0) == 1:
            results[mild] = 0
    
    return results

def calculate_charlson_score(results: Dict[str, int]) -> int:
    """
    Рассчитывает обновлённый балл Charlson.
    """
    total = 0
    for category, weight in CHARLSON_WEIGHTS.items():
        total += results.get(category, 0) * weight
    return total

# ----------------------------------------------------------------------
# ДЕМОНСТРАЦИЯ РАБОТЫ
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # Тестовые данные пациентов
    test_patients = [
        "I21.0, E11.9",                           # Инфаркт + диабет без осл.
        "I21.0, E11.9, C50",                     # Инфаркт + диабет без осл. + рак
        "I21.0, E11.9, E11.6",                   # Инфаркт + диабет без и с осл.
        "I09.9, I50",                            # Сердечная недостаточность
        "G45, I63",                              # Цереброваскулярные
        "J45, M05",                              # Нет совпадений (астма, артрит)
    ]
    
    print("=" * 60)
    print("ТЕСТОВЫЙ СПРАВОЧНИК ИНДЕКСА CHARLSON")
    print("=" * 60)
    print("\nКатегории и их коды:")
    for category, codes in CHARLSON_MAPPINGS.items():
        print(f"\n{category}:")
        print(f"  Кодов: {len(codes)}")
        print(f"  Вес: {CHARLSON_WEIGHTS.get(category, 0)}")
        print(f"  Примеры: {', '.join(codes[:5])}...")
    
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ДЛЯ ТЕСТОВЫХ ПАЦИЕНТОВ")
    print("=" * 60)
    
    for i, codes in enumerate(test_patients, 1):
        print(f"\nПациент {i}:")
        print(f"  Коды: {codes}")
        
        # Оценка
        results = evaluate_patient(codes, CHARLSON_MAPPINGS, CHARLSON_HIERARCHY)
        score = calculate_charlson_score(results)
        
        print("  Категории (1 - есть, 0 - нет):")
        for cat, val in results.items():
            print(f"    {cat}: {val}")
        print(f"  Итоговый балл Charlson (обновлённый): {score}")