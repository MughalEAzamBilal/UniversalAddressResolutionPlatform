from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str
    account_status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    father_name: str
    mother_name: str
    cnic_or_id_card: str
    date_of_birth: date
    # Notice: NEVER expose password_hash or edit_id_hash
