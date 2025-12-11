from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers importados usando rutas absolutas (para que funcionen en Render)
from backend.api.routers.epsilon import router as epsilon_router
from backend.api.routers.sigma import router as sigma_router
from backend.api.routers.poseidon import router as poseidon_router
from backend.api.routers.helios import router as helios_router
from backend.api.routers.user import router as user_router


# Inicializamos FastAPI
app = FastAPI(
    title="OLIMPO API",
    description="API oficial para los modelos Epsilon, Sigma, Poseidón y el Digital Twin HELIOS",
    version="1.0.0"
)

# Configuración de CORS para permitir acceso desde la App móvil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # luego restringiremos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta raíz para verificar funcionamiento
@app.get("/")
def root():
    return {
        "message": "OLIMPO API funcionando correctamente",
        "estado": "OK",
        "modelos": ["Epsilon", "Sigma", "Poseidón", "HELIOS Digital Twin"]
    }


# Registrar todos los routers del backend
app.include_router(epsilon_router)
app.include_router(sigma_router)
app.include_router(poseidon_router)
app.include_router(helios_router)
app.include_router(user_router)
