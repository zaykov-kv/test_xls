import requests
import json

NLM_API_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"


def get_icd10_code_details(code: str):
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

        display_data = data[3] if len(data) > 3 else []

        if display_data and len(display_data[0]) >= 2:
            return {
                "code": display_data[0][1],
                "description": display_data[0][0]
            }

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
        print(f"❌ Ошибка запроса к NLM API: {str(e)}")
        return None


if __name__ == "__main__":
    print("=" * 50)
    print("🧪 ТЕСТИРОВАНИЕ NLM API (ПОИСК ПО КОДУ)")
    print("=" * 50)

    test_codes = ["E11.9", "I10", "C50", "XXXX", "N18"]

    for code in test_codes:
        print(f"\n📋 Проверка кода: {code}")
        details = get_icd10_code_details(code)
        if details:
            print(f"✅ Найден: {details['code']}")
            print(f"   Описание: {details['description']}")
        else:
            print(f"❌ Код не найден")

    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")