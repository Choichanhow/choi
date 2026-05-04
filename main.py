import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

app = FastAPI(title="QUART API", version="0.1.0")

API_KEY = os.getenv("API_KEY", "")


@app.get("/")
async def root():
    return {"message": "Welcome to QUART API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/verify-key")
async def verify_key():
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    return {"message": "API_KEY is configured"}
