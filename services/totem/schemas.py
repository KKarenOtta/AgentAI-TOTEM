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
    audio_base64: str | None = None
    input_mode: str | None = None  # "text" | "audio"
    message_id: str | None = None  # para idempotência depois

class TotemInteractResponse(BaseModel):
    session_id: str
    language: Language
    text: str
    recommendations: Dict[str, Any]
    audio_file: Optional[str] = None
    metrics: Dict[str, Any]

class TotemActivateRequest(BaseModel):
    company_id: str
    session_id: str = Field(default="sim-web")
    profile: Optional[Any] = None  # pode ser seu ProfileModel se quiser

class TotemActivateResponse(BaseModel):
    session_id: str
    language: str
    greeting: str
    next: str  # "listening"

class TotemNPSRequest(BaseModel):
    company_id: str
    session_id: str
    score: int  # 0..10
    comment: str | None = None

class TotemNPSResponse(BaseModel):
    ok: bool
    message: str

class TotemTrackRequest(BaseModel):
    company_id: str
    session_id: str
    event: str  # ex: "action_click", "qr_open", "coupon_generated", "call_attendant"
    action_id: Optional[str] = None
    action_label: Optional[str] = None
    campaign_id: Optional[str] = None
    turn_index: Optional[int] = None
    message_id: Optional[str] = None
    value: Optional[float] = None  # ex: valor estimado/score
    meta: Optional[Dict[str, Any]] = None

class TotemTrackResponse(BaseModel):
    ok: bool = True
    message: str = "tracked"