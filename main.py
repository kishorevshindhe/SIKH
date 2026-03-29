from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine, Base
from auth.routes import router as auth_router
from chat.routes import router as chat_router

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SIKH API",
    description="Secure Intelligent Knowledge Hub",
    version="1.0.0"
)

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router, tags=["Chat"])

@app.get("/")
def home():
    return {"message": "SIKH Backend is running!"}

@app.get("/test-chat", response_class=HTMLResponse)
def test_chat():
    with open("test_chat.html", "r", encoding="utf-8") as f:
        return f.read()