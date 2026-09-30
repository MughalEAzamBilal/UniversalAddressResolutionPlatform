from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


class AdminDashboardStats(BaseModel):
    total_users: int
    total_addresses: int
    active_addresses: int
    inactive_addresses: int
    local_addresses: int
    international_addresses: int
    today_resolutions: int
    failed_resolutions: int


class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    father_name: str
    mother_name: str
    cnic_or_id_card: str
    date_of_birth: str  # YYYY-MM-DD
    role: str = "USER"
    phone: Optional[str] = None


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    account_status: Optional[str] = None
    phone: Optional[str] = None


class AdminPasswordReset(BaseModel):
    new_password: str


class AdminEditIdReset(BaseModel):
    father_name: str
    mother_name: str
    cnic_or_id_card: str
    date_of_birth: str  # YYYY-MM-DD


class AccessLogResponse(BaseModel):
    id: int
    public_id: str
    address_id: Optional[int]
    accessed_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    referrer: Optional[str]
    success: bool

    class Config:
        from_attributes = True


class AdminActionResponse(BaseModel):
    id: int
    admin_user_id: Optional[int]
    action: str
    target_type: str
    target_id: Optional[str]
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
