from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="OLIMPO API",
    description="API oficial para los modelos Epsilon, Sigma, Poseidon y el Digital Twin HELIOS",
    version="1.0.0"
)

# Configuración CORS para permitir conexión desde la App móvil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego lo restringiremos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta de prueba
@app.get("/")
def root():
    return {"message": "OLIMPO API funcionando correctamente", "estado": "OK"}

from api.routers.epsilon import router as epsilon_router
from api.routers.sigma import router as sigma_router
from api.routers.poseidon import router as poseidon_router
from api.routers.helios import router as helios_router
from api.routers.user import router as user_router

app.include_router(epsilon_router)
app.include_router(sigma_router)
app.include_router(poseidon_router)
app.include_router(helios_router)
app.include_router(user_router)

from api.routers import epsilon
app.include_router(epsilon.router)

from api.routers import sigma
app.include_router(sigma.router)

from api.routers import poseidon
app.include_router(poseidon.router)

from api.routers import helios
app.include_router(helios.router)