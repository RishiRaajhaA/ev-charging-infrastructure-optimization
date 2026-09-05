import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from web_app.backend.routes.data_routes import router as data_router
from web_app.backend.routes.opt1_routes import router as opt1_router
from web_app.backend.routes.opt2_routes import router as opt2_router

app = FastAPI(
    title="EV Infrastructure Optimization Decision Support Suite",
    description="Full-stack Operations Research application for EV charging network expansion.",
    version="2.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(data_router)
app.include_router(opt1_router)
app.include_router(opt2_router)

# Mount Frontend static assets
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app.backend.server:app", host="127.0.0.1", port=8000, reload=True)
