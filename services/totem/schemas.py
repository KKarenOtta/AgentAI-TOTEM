from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

Gender = Literal["female", "male", "nonbinary", "unknown"]
Language = Literal["pt", "en", "es"]

class DemographicProfile(BaseModel):
    # Ideal: auto-declarado; se for inferido, indique confidence.
    age_estimate: Optional[int] = Field(default=None, ge=0, le=120)
    age_range: Optional[str] = None  # ex: "18-24", "25-34"...
    gender: Gender = "unknown"        # trate como "presentation"/estimativa
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # extras úteis para marketing
    segment: Optional[str] = None     # ex: "new_visitor", "returning", "vip"
    device: Optional[str] = None      # ex: "totem_kiosk", "mobile"
    locale: Optional[str] = None      # ex: "pt-BR"
    extra: Dict[str, Any] = Field(default_factory=dict)

class TotemInteractRequest(BaseModel):
    company_id: str
    session_id: str
    message: str
    profile: Optional[DemographicProfile] = None
    prefer_audio: bool = True

class TotemInteractResponse(BaseModel):
    session_id: str
    language: Language
    text: str
    recommendations: Dict[str, Any]
    audio_file: Optional[str] = None
    metrics: Dict[str, Any]