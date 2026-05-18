import os
import httpx
from typing import List, Dict, Any, Optional

class MercadoLibreClient:
    """
    TAREA 2: Source client para Mercado Libre Chile (MLC).
    Utiliza la API oficial de Mercado Libre para buscar items.
    """
    
    def __init__(self):
        self.site_id = "MLC" # Chile
        self.base_url = "https://api.mercadolibre.com"
        # Soportar token si está configurado para evitar rate limits
        self.access_token = os.getenv("MERCADO_LIBRE_ACCESS_TOKEN")
        self.timeout = 10.0

    async def search_items(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Busca items en Mercado Libre Chile.
        """
        url = f"{self.base_url}/sites/{self.site_id}/search"
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "condition": "new", # Solo productos nuevos para ÁGORA
        }
        
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=headers)
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
                    
                return normalized_items
                
        except Exception as e:
            # Manejo de error controlado: logueamos pero no rompemos el proceso
            # En un entorno real usaríamos un logger adecuado
            print(f"Error consultando Mercado Libre MLC: {str(e)}")
            return []
