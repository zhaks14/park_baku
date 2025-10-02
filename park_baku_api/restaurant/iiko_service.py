import requests, time

IIKO_LOGIN = "ВАШ_API_LOGIN"
IIKO_BASE_URL = "https://api-ru.iiko.services/api/1"
TOKEN_CACHE = {"token": None, "expires": 0}


def get_token():
    now = time.time()
    if TOKEN_CACHE["token"] and TOKEN_CACHE["expires"] > now:
        return TOKEN_CACHE["token"]

    url = f"{IIKO_BASE_URL}/access_token"
    res = requests.post(url, json={"apiLogin": IIKO_LOGIN})
    res.raise_for_status()
    token = res.json()["token"]

    TOKEN_CACHE["token"] = token
    TOKEN_CACHE["expires"] = now + 3600
    return token


def get_order_by_id(org_id, order_id):
    token = get_token()
    url = f"{IIKO_BASE_URL}/orders/by_id"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"organizationId": org_id, "orderIds": [order_id]}
    res = requests.post(url, headers=headers, json=data)
    res.raise_for_status()
    return res.json()
