"""
SIKH - Secure Intelligent Knowledge Hub
Backend Entry Point (Member 1)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SIKH API",
    description="Secure Intelligent Knowledge Hub - Backend API",
    version="1.0.0"
)

# CORS — allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "SIKH Backend is running 🚀"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# TODO: Register routers here as you build them
# from backend.auth.routes import router as auth_router
# from backend.chat.routes import router as chat_router
# app.include_router(auth_router, prefix="/auth")
# app.include_router(chat_router, prefix="/chat")
