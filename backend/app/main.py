# backend/app/main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from datetime import datetime

from app.deepskin_processor import DeepskinProcessor
from app.gemini_enhancer import GeminiEnhancer

load_dotenv()

app = FastAPI(title="Wound Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

deepskin = DeepskinProcessor()
gemini = GeminiEnhancer(api_key=os.getenv("GOOGLE_API_KEY"))

@app.get("/")
async def root():
    return {"message": "Wound Analysis API", "status": "running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "deepskin": "loaded",
        "gemini": "configured" if gemini.available else "missing API key",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/analyze")
async def analyze_wound(file: UploadFile = File(...)):
    # Read image
    image_bytes = await file.read()
    
    # Deepskin analysis
    deepskin_results = deepskin.process_image(image_bytes)
    
    # Gemini analysis
    gemini_results = None
    if gemini.available and deepskin_results.get('success'):
        gemini_results = gemini.analyze_wound(image_bytes, deepskin_results)
    
    return {
        "filename": file.filename,
        "deepskin": deepskin_results,
        "gemini": gemini_results
    }