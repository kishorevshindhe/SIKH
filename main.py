from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from database.database import engine, Base
from auth.routes import router as auth_router
from chat.routes import router as chat_router
from chat.file_routes import router as file_router
from security.rate_limiter import limiter

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SIKH API",
    description="Secure Intelligent Knowledge Hub",
    version="1.0.0"
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(file_router, tags=["Files"])

@app.get("/")
def home():
    return {"message": "SIKH Backend is running!"}

@app.get("/test-chat", response_class=HTMLResponse)
def test_chat():
    with open("test_chat.html", "r", encoding="utf-8") as f:
        return f.read()