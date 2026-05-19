import os
import sys
import asyncio
import httpx
from datetime import datetime

# Agregar el directorio raíz al path para poder importar backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.database.session import SessionLocal
from backend.agora.price_intelligence.source_clients.meli_oauth import MeliOAuthClient

async def debug_meli_search():
    """
    Script de diagnóstico para investigar el error 403 en las búsquedas de Mercado Libre.
    """
    db = SessionLocal()
    oauth_client = MeliOAuthClient()
    
    # 1. Recuperar token de DB (sin imprimirlo completo)
    access_token = await oauth_client.get_valid_access_token(db)
    has_token = access_token is not None
    
    site_id = "MLC"
    base_url = "https://api.mercadolibre.com"
    query = "tubo pvc sanitario"
    
    tests = [
        # A) Con Authorization Bearer (si hay token)
        {
            "name": "A) With Auth Bearer",
            "url": f"{base_url}/sites/{site_id}/search",
            "params": {"q": query, "limit": 10, "condition": "new"},
            "headers": {
                "Authorization": f"Bearer {access_token}" if has_token else None,
                "Accept": "application/json",
                "User-Agent": "OLIMPO-Agora/1.0"
            },
            "skip": not has_token
        },
        # B) Sin Authorization
        {
            "name": "B) Without Auth",
            "url": f"{base_url}/sites/{site_id}/search",
            "params": {"q": query, "limit": 10, "condition": "new"},
            "headers": {
                "Accept": "application/json",
                "User-Agent": "OLIMPO-Agora/1.0"
            },
            "skip": False
        },
        # C) Con query simple (pvc)
        {
            "name": "C) Simple Query (pvc)",
            "url": f"{base_url}/sites/{site_id}/search",
            "params": {"q": "pvc", "limit": 10, "condition": "new"},
            "headers": {
                "Authorization": f"Bearer {access_token}" if has_token else None,
                "Accept": "application/json",
                "User-Agent": "OLIMPO-Agora/1.0"
            },
            "skip": not has_token
        },
        # D) Sin condition=new
        {
            "name": "D) Without condition=new",
            "url": f"{base_url}/sites/{site_id}/search",
            "params": {"q": query, "limit": 10},
            "headers": {
                "Authorization": f"Bearer {access_token}" if has_token else None,
                "Accept": "application/json",
                "User-Agent": "OLIMPO-Agora/1.0"
            },
            "skip": not has_token
        },
        # E) Con headers mínimos (sin User-Agent)
        {
            "name": "E) Minimal headers (No User-Agent)",
            "url": f"{base_url}/sites/{site_id}/search",
            "params": {"q": query, "limit": 10, "condition": "new"},
            "headers": {
                "Authorization": f"Bearer {access_token}" if has_token else None,
            },
            "skip": not has_token
        }
    ]
    
    print(f"--- MeLi Search Debug Script ---")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Has DB Token: {has_token}")
    print(f"---------------------------------")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for test in tests:
            if test["skip"]:
                print(f"Skipping {test['name']}")
                continue
            
            print(f"\nRunning: {test['name']}")
            print(f"URL: {test['url']}")
            print(f"Params: {test['params']}")
            
            try:
                # Limpiar headers None
                hdrs = {k: v for k, v in test["headers"].items() if v is not None}
                
                response = await client.get(test["url"], params=test["params"], headers=hdrs)
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    print(f"Count API: {len(results)}")
                    for i, item in enumerate(results[:3]):
                        print(f"  [{i}] {item.get('title')}")
                else:
                    print(f"Error Body: {response.text[:200]}")
                    
            except Exception as e:
                print(f"Exception: {str(e)}")
                
    db.close()

if __name__ == "__main__":
    asyncio.run(debug_meli_search())
