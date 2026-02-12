# backend/api/routers/auth.py
# DEPRECATED: Este router ha sido reemplazado por backend/api/routers/auth_google.py
# Se mantiene como wrapper por compatibilidad si fuera necesario, pero main.py debe usar auth_google.

from fastapi import APIRouter
from backend.api.routers.auth_google import router as auth_google_router

# Re-exportamos el router canónico
router = auth_google_router