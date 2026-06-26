from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.features.statistical_analysis.router import router as statistical_router

app = FastAPI(
    title="Olahin API - Automated Preprocessing & Statistical Analysis",
    description=(
        "Sistem backend otomatis untuk mengolah data penelitian: "
        "menerima data, membersihkan (imputasi/outlier), menentukan uji statistik "
        "secara otomatis, menerjemahkan hasil ke Bahasa Indonesia, dan mengekspor laporan Word."
    ),
    version="1.0.0"
)

# Set up CORS middleware to allow easy integration with frontend apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Feature Routers
app.include_router(statistical_router)

@app.get("/", summary="Root Health Check")
async def root():
    return {
        "status": "online",
        "service": "Olahin API Backend",
        "features_loaded": ["statistical-analysis"],
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
