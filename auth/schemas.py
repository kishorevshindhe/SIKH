from pydantic import BaseModel, EmailStr

# Data shape for registering a new user
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

# Data shape for logging in
class UserLogin(BaseModel):
    email: str
    password: str

# What we send back after login
class TokenResponse(BaseModel):
    access_token: str
    token_type: str