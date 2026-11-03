from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from web_app.backend.services.data_service import data_service
from web_app.backend.services.solver_service import solver_service

router = APIRouter(prefix="/api/opt2", tags=["optimization_2"])

class ConnectorAllocationRequest(BaseModel):
    budget: int = Field(500, ge=10, le=10000, description="Total additional connector budget B")
    grouping: str = Field("state", description="'state' (403 regions) or 'country_state' (415 regions)")
    country: Optional[str] = Field("All", description="Country/regional scope ('All', 'US', 'CA', etc.)")

class SensitivityRequest(BaseModel):
    grouping: Optional[str] = Field("state", description="Regional grouping scheme")
    country: Optional[str] = Field("All", description="Country/regional scope ('All', 'US', 'CA', etc.)")

@router.post("/solve")
async def solve_opt2(req: ConnectorAllocationRequest):
    """
    Solves Optimization 2: Regional Infrastructure Connector Allocation
    via Max-Min Fairness MILP.
    """
    try:
        df = data_service.get_df()
        return solver_service.solve_optimization_2(
            df=df,
            budget=req.budget,
            grouping=req.grouping,
            country=req.country or "All"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization 2 execution failed: {str(e)}")

@router.post("/sensitivity")
async def budget_sensitivity(req: Optional[SensitivityRequest] = None):
    """
    Runs budget sensitivity curve (B = 50 to 2000 connectors) proving monotonicity and equity gains.
    """
    try:
        df = data_service.get_df()
        grouping = req.grouping if req and req.grouping else "state"
        country = req.country if req and req.country else "All"
        return solver_service.run_budget_sensitivity(df=df, grouping=grouping, country=country)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Budget sensitivity analysis failed: {str(e)}")
