import os
import httpx
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.agora.price_intelligence.source_clients.meli_oauth import MeliOAuthClient

class MercadoLibreClient:
    """
    TAREA 2: Source client para Mercado Libre Chile (MLC).
    Utiliza la API oficial de Mercado Libre para buscar items.
    """
    
    def __init__(self):
        self.site_id = "MLC" # Chile
        self.base_url = "https://api.mercadolibre.com"
        self.timeout = 10.0
        self.oauth = MeliOAuthClient()

    async def search_items(
        self,
        db: Session,
        query: str,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Busca items en Mercado Libre Chile.
        Retorna un diccionario estructurado con el estado y los resultados.
        """
        # Obtener token válido (de DB o ENV)
        access_token = await self.oauth.get_valid_access_token(db)
        
        url = f"{self.base_url}/sites/{self.site_id}/search"
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "condition": "new", # Solo productos nuevos para ÁGORA
        }
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "OLIMPO-Agora/1.0"
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                
                # Reportar logs seguros para auditoría
                if access_token:
                    print(f"MLC API: Buscando '{query}' (usando OAuth token)")
                else:
                    print(f"MLC API: Buscando '{query}' (sin token - público)")

                if response.status_code == 403:
                    return {
                        "status": "forbidden",
                        "http_status": 403,
                        "raw_count_api": 0,
                        "items": [],
                        "error": "Mercado Libre rejected search request (Forbidden)",
                        "requires_review": True
                    }
                
                if response.status_code == 401:
                    return {
                        "status": "unauthorized",
                        "http_status": 401,
                        "raw_count_api": 0,
                        "items": [],
                        "error": "Mercado Libre token unauthorized or expired"
                    }

                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                normalized_items = []
                
                for item in results:
                    price = item.get("price")
                    title = item.get("title")
                    
                    if not price or price <= 0 or not title:
                        continue
                        
                    normalized_items.append({
                        "source": "mercado_libre_mlc",
                        "source_type": "api",
                        "source_item_id": item.get("id"),
                        "title": title,
                        "url": item.get("permalink"),
                        "price": float(price),
                        "currency": item.get("currency_id", "CLP"),
                        "seller_id": str(item.get("seller", {}).get("id")) if item.get("seller") else None,
                        "condition": item.get("condition"),
                        "raw": {
                            "category_id": item.get("category_id"),
                            "domain_id": item.get("domain_id"),
                            "catalog_listing": item.get("catalog_listing"),
                        }
                    })
                    
                return {
                    "status": "ok" if normalized_items else "empty",
                    "http_status": response.status_code,
                    "raw_count_api": len(results),
                    "items": normalized_items,
                    "error": None
                }
                
        except httpx.HTTPStatusError as e:
            print(f"Error HTTP consultando Mercado Libre MLC: {str(e)}")
            return {
                "status": "error",
                "http_status": e.response.status_code,
                "raw_count_api": 0,
                "items": [],
                "error": f"HTTP Error: {str(e)}"
            }
        except Exception as e:
            print(f"Error consultando Mercado Libre MLC: {str(e)}")
            return {
                "status": "error",
                "http_status": 500,
                "raw_count_api": 0,
                "items": [],
                "error": f"Unexpected error: {str(e)}"
            }

