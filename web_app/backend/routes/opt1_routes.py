from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from web_app.backend.services.data_service import data_service
from web_app.backend.services.solver_service import solver_service

router = APIRouter(prefix="/api/opt1", tags=["optimization_1"])

class Opt1Request(BaseModel):
    n_hubs: int = Field(10, ge=1, le=50, description="Number of hubs to select (K)")
    radius_km: float = Field(50.0, ge=5.0, le=500.0, description="Coverage radius in km")
    n_candidates: int = Field(100, ge=10, le=300, description="Number of candidate clusters")
    country: Optional[str] = Field("All", description="Country/geographic filter or 'All'")

class KSensitivityRequest(BaseModel):
    radius_km: float = Field(50.0, ge=5.0, le=500.0)
    n_candidates: int = Field(100, ge=10, le=300)
    country: Optional[str] = Field("All")

class RadiusSensitivityRequest(BaseModel):
    n_hubs: int = Field(10, ge=1, le=50)
    n_candidates: int = Field(100, ge=10, le=300)
    country: Optional[str] = Field("All")

class CandidateSensitivityRequest(BaseModel):
    n_hubs: int = Field(10, ge=1, le=50)
    radius_km: float = Field(50.0, ge=5.0, le=500.0)
    country: Optional[str] = Field("All")

@router.post("/solve")
async def solve_opt1(req: Opt1Request):
    try:
        df = data_service.get_df()
        res = solver_service.solve_optimization_1(
            df=df,
            n_hubs=req.n_hubs,
            radius_km=req.radius_km,
            n_candidates=req.n_candidates,
            country=req.country or "All"
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization 1 execution failed: {str(e)}")

@router.post("/sensitivity/k")
async def k_sensitivity(req: KSensitivityRequest):
    try:
        df = data_service.get_df()
        return solver_service.run_k_sensitivity(
            df=df,
            radius_km=req.radius_km,
            n_candidates=req.n_candidates,
            country=req.country or "All"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"K-sensitivity failed: {str(e)}")

@router.post("/sensitivity/radius")
async def radius_sensitivity(req: RadiusSensitivityRequest):
    try:
        df = data_service.get_df()
        return solver_service.run_radius_sensitivity(
            df=df,
            n_hubs=req.n_hubs,
            n_candidates=req.n_candidates,
            country=req.country or "All"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Radius-sensitivity failed: {str(e)}")

@router.post("/sensitivity/candidates")
async def candidate_sensitivity(req: CandidateSensitivityRequest):
    try:
        df = data_service.get_df()
        return solver_service.run_candidate_sensitivity(
            df=df,
            n_hubs=req.n_hubs,
            radius_km=req.radius_km,
            country=req.country or "All"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Candidate-sensitivity failed: {str(e)}")
