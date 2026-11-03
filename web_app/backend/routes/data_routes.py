from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional
from web_app.backend.services.data_service import data_service

router = APIRouter(prefix="/api", tags=["data"])

class UploadCSVRequest(BaseModel):
    filename: str = Field(..., description="Uploaded CSV filename")
    csv_text: str = Field(..., description="Raw CSV string content")

@router.get("/stats")
async def get_stats():
    try:
        return data_service.get_summary_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter-options")
async def get_filter_options():
    try:
        return data_service.get_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stations")
async def get_stations(
    limit: int = Query(1000, ge=10, le=50000),
    country: Optional[str] = None,
    state: Optional[str] = None,
    operator: Optional[str] = None,
    status: Optional[str] = None
):
    try:
        return data_service.get_stations_sample(
            limit=limit,
            country=country,
            state=state,
            operator=operator,
            status=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-dataset")
async def upload_dataset(req: UploadCSVRequest):
    if not req.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")
    try:
        content_bytes = req.csv_text.encode("utf-8")
        stats = data_service.load_custom_data(content_bytes, req.filename)
        return {
            "message": f"Successfully loaded dataset '{req.filename}'",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload error: {str(e)}")

@router.post("/reset-dataset")
async def reset_dataset():
    try:
        stats = data_service.reset_to_default()
        return {
            "message": "Reset back to default sample dataset.",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
