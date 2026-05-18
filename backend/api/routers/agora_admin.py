from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from typing import List, Optional, Dict, Any
import os
import shutil
import tempfile
import asyncio
from pydantic import BaseModel

from backend.api.db_deps import get_db
from backend.agora.admin_security import validate_agora_admin_token
from backend.agora.price_intelligence.manual_ingestion import ManualIngestionService
from backend.agora.price_intelligence.snapshot_builder import SnapshotBuilder
from backend.agora.price_intelligence.price_observer import PriceObserver
from backend.agora.price_intelligence.source_clients.meli_oauth import MeliOAuthClient
from backend.database.models.agora import AgoraPriceObservation, AgoraFamilyMonthlySnapshot

router = APIRouter(
    prefix="/agora/v2/admin",
    tags=["agora_v2_admin"],
    dependencies=[Depends(validate_agora_admin_token)]
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

@router.get("/history-health")
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
            "error": str(e)
        }

@router.post("/price-observations/import-csv")
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

@router.post("/snapshots/build")
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

@router.post("/snapshots/build-bulk")
async def build_bulk_snapshots(
    req: SnapshotBulkBuildRequest,
    db: Session = Depends(get_db)
):
    """
    TAREA 2: Construir snapshots masivos para un mes.
    """
    # Parse month dates
    from datetime import datetime, timezone
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

@router.post("/observe-family")
async def observe_family(
    req: ObserveFamilyRequest,
    db: Session = Depends(get_db)
):
    """
    TAREA 8: Disparar observación real para una familia.
    """
    observer = PriceObserver()
    result = await observer.observe_family_prices(
        db, req.market_id, req.product_id, req.family_id, 
        source_id=req.source_id, build_snapshot=req.build_snapshot
    )
    return result

@router.post("/observe-market")
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

@router.get("/observations")
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

@router.get("/snapshots")
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

@router.get("/meli/oauth/url")
async def get_meli_oauth_url():
    """
    TAREA 2: Obtener URL de autorización de Mercado Libre.
    """
    url = meli_oauth.build_meli_authorization_url()
    return {
        "authorization_url": url,
        "redirect_uri": meli_oauth.redirect_uri,
        "client_id_present": meli_oauth.client_id is not None
    }

@router.get("/meli/oauth/callback")
async def meli_oauth_callback(code: str = Query(...)):
    """
    TAREA 2: Intercambiar code por token.
    """
    result = await meli_oauth.exchange_code_for_token(code)
    
    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=f"Error en OAuth de Mercado Libre: {result.get('error_description', result['error'])}"
        )
        
    return {
        "ok": True,
        "has_access_token": "access_token" in result,
        "has_refresh_token": "refresh_token" in result,
        "expires_in": result.get("expires_in"),
        "user_id": str(result.get("user_id"))
    }

@router.get("/meli/status")
async def get_meli_status():
    """
    TAREA 2: Estado de la configuración de MLC.
    """
    return {
        "configured": all([meli_oauth.client_id, meli_oauth.client_secret, meli_oauth.redirect_uri]),
        "has_client_id": meli_oauth.client_id is not None,
        "has_client_secret": meli_oauth.client_secret is not None,
        "has_redirect_uri": meli_oauth.redirect_uri is not None,
        "has_env_access_token": os.getenv("MERCADO_LIBRE_ACCESS_TOKEN") is not None
    }
