from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=100)
    father_name: str = Field(..., min_length=2, max_length=100)
    mother_name: str = Field(..., min_length=2, max_length=100)
    cnic_or_id_card: str = Field(..., min_length=3, max_length=50)
    date_of_birth: date
    phone: Optional[str] = None


class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str


class EditIdLoginRequest(BaseModel):
    edit_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
    role: str


class EditSessionTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
