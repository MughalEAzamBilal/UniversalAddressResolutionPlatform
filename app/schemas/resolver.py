from pydantic import BaseModel
from typing import Optional, Dict


class ResolutionResponse(BaseModel):
    public_id: str
    address_type: str
    location_scope: str
    display_text: str
    city: str
    country: str
    postal_code: Optional[str] = None
    destination_url: Optional[str] = None
    driving_directions_url: Optional[str] = None
    redirect_seconds: int = 3
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    all_formats: Optional[Dict[str, str]] = None


class ResolutionRequest(BaseModel):
    public_id: str
