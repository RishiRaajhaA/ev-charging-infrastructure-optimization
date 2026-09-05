from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from web_app.backend.services.data_service import data_service
from web_app.backend.services.solver_service import solver_service

router = APIRouter(prefix="/api/opt2", tags=["optimization_2"])

class Opt2Request(BaseModel):
    budget: int = Field(500, ge=1, le=10000, description="Total connector budget B")

@router.post("/solve")
async def solve_opt2(req: Opt2Request):
    try:
        df = data_service.get_df()
        res = solver_service.solve_optimization_2(df=df, budget=req.budget)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization 2 execution failed: {str(e)}")

@router.post("/sensitivity")
async def budget_sensitivity():
    try:
        df = data_service.get_df()
        return solver_service.run_budget_sensitivity(df=df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Budget sensitivity failed: {str(e)}")
