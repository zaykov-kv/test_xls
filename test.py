import requests
import json

CLIENT_ID = "7f3bb244-88ec-4bb8-b83b-9096618e7b78_593e1829-52d0-48e8-968f-f9ab08bf2fa2"
CLIENT_SECRET = "h1W0tyhQKKsNE2HxAX6DUoj655VwE67YIredW522D0I="

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
WHO_SEARCH_URL = "https://id.who.int/icd/entity/search"


def get_token():
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'icdapi_access',
        'grant_type': 'client_credentials'
    }
    response = requests.post(TOKEN_URL, data=payload, timeout=10, verify=False)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None


def test_search(token, search_term="diabetes"):
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Accept-Language': 'en',
        'API-Version': 'v2'
    }
    params = {"q": search_term, "maxResults": 5}
    
    response = requests.get(WHO_SEARCH_URL, headers=headers, params=params, timeout=15, verify=False)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📋 ПОЛНЫЙ ОТВЕТ:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        
        # Проверяем структуру
        print(f"\n📋 Ключи верхнего уровня: {list(data.keys())}")
        
        if "destinationEntities" in data:
            print(f"\n📋 Найдено записей: {len(data['destinationEntities'])}")
            for i, item in enumerate(data['destinationEntities'][:3]):
                print(f"\n--- Элемент {i+1} ---")
                print(f"  Ключи: {list(item.keys())}")
                for key in ['theCode', 'code', 'id', 'title']:
                    if key in item:
                        print(f"  {key}: {item[key]}")
    else:
        print(f"Ошибка: {response.text}")


if __name__ == "__main__":
    token = get_token()
    if token:
        test_search(token, "diabetes")
    else:
        print("❌ Не удалось получить токен")