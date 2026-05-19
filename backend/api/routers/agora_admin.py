from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, inspect
from typing import List, Optional, Dict, Any
import os
import shutil
import tempfile
import asyncio
from pydantic import BaseModel
from datetime import datetime, timezone

from backend.api.db_deps import get_db
from backend.agora.admin_security import validate_agora_admin_token
from backend.agora.price_intelligence.manual_ingestion import ManualIngestionService
from backend.agora.price_intelligence.snapshot_builder import SnapshotBuilder
from backend.agora.price_intelligence.price_observer import PriceObserver
from backend.agora.price_intelligence.source_clients.meli_oauth import MeliOAuthClient
from backend.agora.agora_metadata_service import AgoraMetadataService
from backend.database.models.agora import AgoraPriceObservation, AgoraFamilyMonthlySnapshot

# NOTA: Se remueve la dependencia global del router para permitir que el callback de OAuth 
# sea accesible sin el header X-AGORA-ADMIN-TOKEN (ya que Mercado Libre redirige vía navegador).
router = APIRouter(
    prefix="/agora/v2/admin",
    tags=["agora_v2_admin"]
)

meli_oauth = MeliOAuthClient()

class SnapshotBuildRequest(BaseModel):
    market_id: str
    product_id: str
    family_id: str
    month: str # YYYY-MM

class SnapshotBulkBuildRequest(BaseModel):
    month: str # YYYY-MM
    market_id: Optional[str] = None
    product_id: Optional[str] = None

class ObserveFamilyRequest(BaseModel):
    market_id: str
    product_id: str
    family_id: str
    source_id: str = "mercado_libre_mlc"
    build_snapshot: bool = True

class ObserveMarketRequest(BaseModel):
    market_id: str
    source_id: str = "mercado_libre_mlc"
    limit_families: int = 20

@router.get("/history-health", dependencies=[Depends(validate_agora_admin_token)])
async def get_history_health(db: Session = Depends(get_db)):
    """
    TAREA 2: Health operativo de histórico.
    """
    try:
        obs_count = db.query(func.count(AgoraPriceObservation.id)).scalar()
        snap_count = db.query(func.count(AgoraFamilyMonthlySnapshot.id)).scalar()
        
        last_obs = db.query(AgoraPriceObservation).order_by(desc(AgoraPriceObservation.observed_at)).first()
        last_snap = db.query(AgoraFamilyMonthlySnapshot).order_by(desc(AgoraFamilyMonthlySnapshot.month)).first()
        
        return {
            "ok": True,
            "tables": {
                "agora_price_observations": True,
                "agora_family_monthly_snapshots": True
            },
            "observations_count": obs_count,
            "snapshots_count": snap_count,
            "last_observation_at": last_obs.observed_at.isoformat() if last_obs else None,
            "last_snapshot_month": last_snap.month if last_snap else None
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "metadata_error": "agora_metadata table not available" if "agora_metadata" in str(e) else None
        }

@router.post("/price-observations/import-csv", dependencies=[Depends(validate_agora_admin_token)])
async def import_price_observations(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    TAREA 2: Carga manual controlada por CSV.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un CSV.")
        
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
        
    try:
        service = ManualIngestionService()
        result = service.ingest_price_observations_csv(db, tmp_path)
        return result
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.post("/snapshots/build", dependencies=[Depends(validate_agora_admin_token)])
async def build_snapshot(
    req: SnapshotBuildRequest,
    db: Session = Depends(get_db)
):
    """
    TAREA 2: Construir snapshot mensual para una familia.
    """
    builder = SnapshotBuilder()
    snap = builder.build_monthly_snapshot(
        db, req.market_id, req.product_id, req.family_id, req.month
    )
    
    if not snap:
        return {
            "ok": False,
            "message": "No se encontraron observaciones para generar el snapshot.",
            "month": req.month
        }
        
    return {
        "ok": True,
        "snapshot_created": True,
        "market_id": snap.market_id,
        "product_id": snap.product_id,
        "family_id": snap.family_id,
        "month": snap.month,
        "sample_size": snap.sample_size,
        "data_status": snap.data_status
    }

@router.post("/snapshots/build-bulk", dependencies=[Depends(validate_agora_admin_token)])
async def build_bulk_snapshots(
    req: SnapshotBulkBuildRequest,
    db: Session = Depends(get_db)
):
    """
    TAREA 2: Construir snapshots masivos para un mes.
    """
    # Parse month dates
    year_str, month_str = req.month.split('-')
    y, m = int(year_str), int(month_str)
    start_date = datetime(y, m, 1, tzinfo=timezone.utc)
    if m == 12:
        end_date = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(y, m + 1, 1, tzinfo=timezone.utc)
        
    stmt = select(
        AgoraPriceObservation.market_id, 
        AgoraPriceObservation.product_id, 
        AgoraPriceObservation.family_id
    ).where(
        AgoraPriceObservation.observed_at >= start_date,
        AgoraPriceObservation.observed_at < end_date
    ).distinct()
    
    targets = db.execute(stmt).all()
    
    builder = SnapshotBuilder()
    count = 0
    errors = 0
    
    for t in targets:
        # Filtrar si se proveyó market/product
        if req.market_id and t.market_id != req.market_id: continue
        if req.product_id and t.product_id != req.product_id: continue
        
        try:
            snap = builder.build_monthly_snapshot(db, t.market_id, t.product_id, t.family_id, req.month)
            if snap: count += 1
        except Exception:
            errors += 1
            
    return {
        "ok": True,
        "month": req.month,
        "snapshots_built": count,
        "errors": errors,
        "families_processed": len(targets)
    }

@router.post("/observe-family", dependencies=[Depends(validate_agora_admin_token)])
async def observe_family(
    req: ObserveFamilyRequest,
    db: Session = Depends(get_db)
):
    """
    TAREA 8: Disparar observación real para una familia.
    """
    try:
        observer = PriceObserver()
        result = await observer.observe_family_prices(
            db, req.market_id, req.product_id, req.family_id, 
            source_id=req.source_id, build_snapshot=req.build_snapshot
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "source_status": "error",
            "source_error": str(e),
            "token_source": "unknown"
        }

@router.post("/observe-market", dependencies=[Depends(validate_agora_admin_token)])
async def observe_market(
    req: ObserveMarketRequest,
    db: Session = Depends(get_db)
):
    """
    TAREA 8: Disparar observación masiva para un mercado.
    """
    from backend.agora.family_catalog_service import FamilyCatalogService
    catalog = FamilyCatalogService()
    
    # Resolver ID canónico si es necesario
    c_market_id = catalog.resolve_market_id(req.market_id)
    products = catalog.list_products_by_market(c_market_id)
    
    observer = PriceObserver()
    total_processed = 0
    results = []
    
    for p in products:
        if total_processed >= req.limit_families: break
        
        families = catalog.list_families_by_product(c_market_id, p["product_id"])
        for f in families:
            if total_processed >= req.limit_families: break
            
            res = await observer.observe_family_prices(
                db, c_market_id, p["product_id"], f["family_id"], 
                source_id=req.source_id, build_snapshot=True
            )
            results.append({
                "family_id": f["family_id"],
                "inserted": res.get("inserted", 0),
                "data_status": res.get("data_status")
            })
            total_processed += 1
            # Rate limit preventivo para no saturar fuente externa
            await asyncio.sleep(0.5)
            
    return {
        "ok": True,
        "market_id": c_market_id,
        "families_processed": total_processed,
        "summary": results
    }

@router.get("/observations", dependencies=[Depends(validate_agora_admin_token)])
async def list_observations(
    market_id: Optional[str] = None,
    product_id: Optional[str] = None,
    family_id: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(AgoraPriceObservation)
    if market_id: query = query.filter(AgoraPriceObservation.market_id == market_id)
    if product_id: query = query.filter(AgoraPriceObservation.product_id == product_id)
    if family_id: query = query.filter(AgoraPriceObservation.family_id == family_id)
    
    results = query.order_by(desc(AgoraPriceObservation.observed_at)).limit(limit).all()
    return results

@router.get("/snapshots", dependencies=[Depends(validate_agora_admin_token)])
async def list_snapshots(
    market_id: Optional[str] = None,
    product_id: Optional[str] = None,
    family_id: Optional[str] = None,
    month: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(AgoraFamilyMonthlySnapshot)
    if market_id: query = query.filter(AgoraFamilyMonthlySnapshot.market_id == market_id)
    if product_id: query = query.filter(AgoraFamilyMonthlySnapshot.product_id == product_id)
    if family_id: query = query.filter(AgoraFamilyMonthlySnapshot.family_id == family_id)
    if month: query = query.filter(AgoraFamilyMonthlySnapshot.month == month)
    
    results = query.order_by(desc(AgoraFamilyMonthlySnapshot.month)).limit(limit).all()
    return results

# --- Mercado Libre OAuth ---

@router.get("/meli/oauth/url", dependencies=[Depends(validate_agora_admin_token)])
async def get_meli_oauth_url(state: Optional[str] = Query(None)):
    """
    TAREA 2: Obtener URL de autorización de Mercado Libre.
    """
    url = meli_oauth.build_meli_authorization_url(state=state)
    return {
        "authorization_url": url,
        "redirect_uri": meli_oauth.redirect_uri,
        "client_id_present": meli_oauth.client_id is not None
    }

@router.get("/meli/oauth/callback")
async def meli_oauth_callback(
    code: str = Query(...), 
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    TAREA 2: Intercambiar code por token.
    LIBERADO: Accesible sin token administrativo para permitir redirección de navegador.
    """
    result = await meli_oauth.exchange_code_for_token(db, code)
    
    # TAREA 3: Respuesta explícita ante falla o falta de persistencia
    if "error" in result:
        return {
            "ok": False,
            "persisted": False,
            "token_source": "none",
            "error": result.get('error_description', result['error']),
            "state": state
        }
        
    # Si no persistió, lo tratamos como error aunque tengamos el token en memoria un instante
    if not result.get("persisted"):
        return {
            "ok": False,
            "persisted": False,
            "token_source": "none",
            "error": "Token received but could not be persisted to database.",
            "state": state
        }
        
    return {
        "ok": True,
        "has_access_token": "access_token" in result,
        "has_refresh_token": "refresh_token" in result,
        "expires_in": result.get("expires_in"),
        "user_id": str(result.get("user_id", "")),
        "persisted": True,
        "token_source": "db",
        "state": state
    }

@router.get("/meli/status", dependencies=[Depends(validate_agora_admin_token)])
async def get_meli_status(db: Session = Depends(get_db)):
    """
    TAREA 2: Estado de la configuración de MLC.
    """
    try:
        # 1. Verificar configuración base de ENV
        config_ok = all([meli_oauth.client_id, meli_oauth.client_secret, meli_oauth.redirect_uri])
        
        # 2. Verificar existencia de tabla
        inspector = inspect(db.get_bind())
        if "agora_metadata" not in inspector.get_table_names():
            return {
                "configured": config_ok,
                "has_client_id": meli_oauth.client_id is not None,
                "has_client_secret": meli_oauth.client_secret is not None,
                "has_redirect_uri": meli_oauth.redirect_uri is not None,
                "has_env_access_token": os.getenv("MERCADO_LIBRE_ACCESS_TOKEN") is not None,
                "has_db_access_token": False,
                "has_db_refresh_token": False,
                "expires_at": None,
                "is_expired": None,
                "token_source": "env" if os.getenv("MERCADO_LIBRE_ACCESS_TOKEN") else "none",
                "metadata_error": "agora_metadata table not available"
            }

        # 3. Consultar tokens en DB con alta tolerancia
        meta_access = None
        meta_refresh = None
        try:
            meta_access = AgoraMetadataService.get(db, "meli_access_token")
            meta_refresh = AgoraMetadataService.get(db, "meli_refresh_token")
        except Exception as e:
            print(f"MLC Status: Error consultando service: {str(e)}")

        token_source = "none"
        is_expired = None
        expires_at_iso = None
        has_db_access = False
        has_db_refresh = False
        
        if meta_access and hasattr(meta_access, 'value') and meta_access.value:
            has_db_access = True
            token_source = "db"
            
            # Procesamiento robusto de fecha
            if hasattr(meta_access, 'expires_at') and meta_access.expires_at:
                try:
                    expires_at = meta_access.expires_at
                    # Si viene como string, intentar parsear (SQLite fallback)
                    if isinstance(expires_at, str):
                        from datetime import fromisoformat
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

                    # Normalizar aware
                    if hasattr(expires_at, 'tzinfo') and expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    
                    if hasattr(expires_at, 'isoformat'):
                        is_expired = expires_at < datetime.now(timezone.utc)
                        expires_at_iso = expires_at.isoformat()
                except Exception as e:
                    print(f"MLC Status: Error procesando fecha expiración: {str(e)}")
                    is_expired = True # Por seguridad si no podemos leerla
                    
        elif os.getenv("MERCADO_LIBRE_ACCESS_TOKEN"):
            token_source = "env"

        if meta_refresh and hasattr(meta_refresh, 'value') and meta_refresh.value:
            has_db_refresh = True

        return {
            "configured": config_ok,
            "has_client_id": meli_oauth.client_id is not None,
            "has_client_secret": meli_oauth.client_secret is not None,
            "has_redirect_uri": meli_oauth.redirect_uri is not None,
            "has_env_access_token": os.getenv("MERCADO_LIBRE_ACCESS_TOKEN") is not None,
            "has_db_access_token": has_db_access,
            "has_db_refresh_token": has_db_refresh,
            "expires_at": expires_at_iso,
            "is_expired": is_expired,
            "token_source": token_source
        }
    except Exception as e:
        # TAREA 5: No caer en 500 bajo ninguna circunstancia
        return {
            "configured": all([meli_oauth.client_id, meli_oauth.client_secret, meli_oauth.redirect_uri]),
            "token_source": "error",
            "metadata_error": f"Error fatal consultando status: {str(e)}"
        }

