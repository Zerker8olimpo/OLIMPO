import os
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from backend.agora.agora_metadata_service import AgoraMetadataService
from sqlalchemy.orm import Session

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
        
    def build_meli_authorization_url(self, state: Optional[str] = None) -> str:
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
        if state:
            params["state"] = state
            
        return f"{self.base_auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, db: Session, code: str) -> Dict[str, Any]:
        """
        Intercambia el code obtenido por un access_token y refresh_token y los persiste.
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
            result = response.json()
            
            if "access_token" in result:
                self._persist_tokens(db, result)
                
            return result

    def _persist_tokens(self, db: Session, token_data: Dict[str, Any]):
        """Guarda los tokens en la base de datos."""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 21600))
        
        AgoraMetadataService.set(db, "meli_access_token", token_data["access_token"], expires_at=expires_at)
        if "refresh_token" in token_data:
            AgoraMetadataService.set(db, "meli_refresh_token", token_data["refresh_token"])
        if "user_id" in token_data:
            AgoraMetadataService.set(db, "meli_user_id", str(token_data["user_id"]))

    async def get_valid_access_token(self, db: Session) -> Optional[str]:
        """
        Retorna un access_token válido, refrescándolo si es necesario.
        """
        # 1. Intentar de DB
        meta_token = AgoraMetadataService.get(db, "meli_access_token")
        if meta_token and meta_token.value:
            # Si expira en menos de 5 minutos, refrescar
            if meta_token.expires_at and meta_token.expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                return meta_token.value
            
            # Intentar refrescar
            meta_refresh = AgoraMetadataService.get(db, "meli_refresh_token")
            if meta_refresh and meta_refresh.value:
                print("MLC: Refrescando access_token expirado...")
                refresh_result = await self.refresh_meli_access_token(db, meta_refresh.value)
                if "access_token" in refresh_result:
                    return refresh_result["access_token"]

        # 2. Fallback a ENV
        return os.getenv("MERCADO_LIBRE_ACCESS_TOKEN")

    async def refresh_meli_access_token(self, db: Session, refresh_token: str) -> Dict[str, Any]:
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
            result = response.json()
            
            if "access_token" in result:
                self._persist_tokens(db, result)
                
            return result
