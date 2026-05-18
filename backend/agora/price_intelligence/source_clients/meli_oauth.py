import os
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlencode

class MeliOAuthClient:
    """
    TAREA 1: Cliente OAuth para Mercado Libre.
    Maneja el flujo de autorización y gestión de tokens.
    """
    
    def __init__(self):
        self.base_auth_url = "https://auth.mercadolibre.cl/authorization"
        self.token_url = "https://api.mercadolibre.com/oauth/token"

    @property
    def client_id(self) -> Optional[str]:
        return os.getenv("MELI_CLIENT_ID")

    @property
    def client_secret(self) -> Optional[str]:
        return os.getenv("MELI_CLIENT_SECRET")

    @property
    def redirect_uri(self) -> Optional[str]:
        return os.getenv("MELI_REDIRECT_URI")
        
    def build_meli_authorization_url(self) -> str:
        """
        Construye la URL para redirigir al usuario y obtener el code.
        """
        c_id = self.client_id
        r_uri = self.redirect_uri
        
        if not c_id or not r_uri:
            return ""
            
        params = {
            "response_type": "code",
            "client_id": c_id,
            "redirect_uri": r_uri
        }
        return f"{self.base_auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Intercambia el code obtenido por un access_token y refresh_token.
        """
        c_id = self.client_id
        c_secret = self.client_secret
        r_uri = self.redirect_uri
        
        if not all([c_id, c_secret, r_uri]):
            return {"error": "Missing MLC credentials in environment"}
            
        data = {
            "grant_type": "authorization_code",
            "client_id": c_id,
            "client_secret": c_secret,
            "code": code,
            "redirect_uri": r_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data)
            return response.json()

    async def refresh_meli_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Usa el refresh_token para obtener un nuevo access_token.
        """
        c_id = self.client_id
        c_secret = self.client_secret
        
        if not all([c_id, c_secret]):
            return {"error": "Missing MLC credentials in environment"}
            
        data = {
            "grant_type": "refresh_token",
            "client_id": c_id,
            "client_secret": c_secret,
            "refresh_token": refresh_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data)
            return response.json()
