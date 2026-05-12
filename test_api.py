"""
Ejecuta con: python test_api.py
"""
import os
import sys
import requests

# forzar UTF-8 en la salida de Windows
sys.stdout.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

KEY = os.environ.get("ITAD_API_KEY", "")

print("=== Test IsThereAnyDeal API ===\n")

if not KEY:
    print("ERROR: ITAD_API_KEY no encontrada en .env")
    sys.exit(1)

print(f"Key cargada: {KEY[:8]}...{KEY[-4:]}\n")

try:
    url = "https://api.isthereanydeal.com/deals/v2"
    params = {"key": KEY, "limit": 5, "country": "US", "sort": "-cut"}

    print(f"Conectando a {url}...")
    resp = requests.get(url, params=params, timeout=15)

    print(f"Status HTTP: {resp.status_code}\n")

    if resp.status_code == 200:
        data = resp.json()
        items = data.get("list") or []
        print(f"OK - {len(items)} juegos recibidos\n")
        for item in items[:5]:
            deal  = item.get("deal") or {}
            shop  = deal.get("shop") or {}
            price = deal.get("price") or {}
            cut   = deal.get("cut") or 0
            curr  = price.get("currency", "USD")
            print(f"  - {item.get('title')} | -{cut}% | {curr} {price.get('amount')} | {shop.get('name')}")
    elif resp.status_code == 401:
        print("ERROR 401: API key invalida.")
        print(resp.text)
    else:
        print(f"ERROR {resp.status_code}:")
        print(resp.text[:500])

except requests.exceptions.ConnectionError as e:
    print(f"ERROR: Sin conexion: {e}")
except requests.exceptions.Timeout:
    print("ERROR: Timeout")
except Exception as e:
    print(f"ERROR inesperado: {e}")
