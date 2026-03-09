from __future__ import annotations
from typing import Dict, Any, List
from pydantic import BaseModel


class ModelRunResponse(BaseModel):
    kpis: Dict[str, Any]
    warnings: List[str]
    interpretation: str
    execution_metadata: Dict[str, Any]