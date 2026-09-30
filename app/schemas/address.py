from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class AddressBase(BaseModel):
    address_type: str = Field(default="DELIVERY")
    location_scope: str = Field(default="LOCAL")
    visibility: str = Field(default="PUBLIC")

    recipient_name: Optional[str] = Field(None, max_length=128)
    business_name: Optional[str] = Field(None, max_length=128)

    country: str = Field(default="Pakistan", max_length=128)
    country_code: str = Field(default="PK", max_length=8)
    province_state: Optional[str] = Field(None, max_length=128)
    region_division: Optional[str] = Field(None, max_length=128)
    district: Optional[str] = Field(None, max_length=128)
    tehsil: Optional[str] = Field(None, max_length=128)
    city: str = Field(..., min_length=1, max_length=128)
    town: Optional[str] = Field(None, max_length=128)
    area: Optional[str] = Field(None, max_length=128)
    locality: Optional[str] = Field(None, max_length=128)

    street: Optional[str] = Field(None, max_length=128)
    road: Optional[str] = Field(None, max_length=128)
    house_number: Optional[str] = Field(None, max_length=64)
    building: Optional[str] = Field(None, max_length=128)
    floor: Optional[str] = Field(None, max_length=32)
    flat: Optional[str] = Field(None, max_length=32)
    landmark: Optional[str] = Field(None, max_length=255)
    postal_code: Optional[str] = Field(None, max_length=32)

    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

    destination_url: Optional[str] = Field(None, max_length=1024)
    redirect_seconds: int = Field(default=3)

    @field_validator("redirect_seconds")
    @classmethod
    def validate_redirect_seconds(cls, v: int) -> int:
        allowed = [0, 1, 2, 3, 5, 10, 15, 30]
        if v not in allowed:
            raise ValueError(f"redirect_seconds must be one of {allowed}")
        return v

    @field_validator("address_type")
    @classmethod
    def validate_address_type(cls, v: str) -> str:
        allowed = ["PERSONAL", "RESIDENTIAL", "DELIVERY", "BUSINESS", "POSTAL", "LANDMARK", "TEMPORARY", "OTHER"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"address_type must be one of {allowed}")
        return v_upper

    @field_validator("location_scope")
    @classmethod
    def validate_location_scope(cls, v: str) -> str:
        allowed = ["LOCAL", "INTERNATIONAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"location_scope must be one of {allowed}")
        return v_upper

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        allowed = ["PUBLIC", "PRIVATE", "UNLISTED"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"visibility must be one of {allowed}")
        return v_upper


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    address_type: Optional[str] = None
    location_scope: Optional[str] = None
    visibility: Optional[str] = None
    recipient_name: Optional[str] = None
    business_name: Optional[str] = None

    country: Optional[str] = None
    country_code: Optional[str] = None
    province_state: Optional[str] = None
    region_division: Optional[str] = None
    district: Optional[str] = None
    tehsil: Optional[str] = None
    city: Optional[str] = None
    town: Optional[str] = None
    area: Optional[str] = None
    locality: Optional[str] = None

    street: Optional[str] = None
    road: Optional[str] = None
    house_number: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    flat: Optional[str] = None
    landmark: Optional[str] = None
    postal_code: Optional[str] = None

    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

    destination_url: Optional[str] = None
    redirect_seconds: Optional[int] = None
    is_active: Optional[bool] = None


class AddressResponse(AddressBase):
    id: int
    public_id: str
    user_id: int
    address_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AddressVersionResponse(BaseModel):
    id: int
    version_number: int
    address_snapshot: str
    created_at: datetime
    changed_by: Optional[int] = None

    class Config:
        from_attributes = True
