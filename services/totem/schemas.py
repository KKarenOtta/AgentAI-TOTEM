from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

Gender = Literal["female", "male", "nonbinary", "unknown"]
Language = Literal["pt", "en", "es"]


class DemographicProfile(BaseModel):
    age_estimate: Optional[int] = Field(default=None, ge=0, le=120)
    age_range: Optional[str] = None
    gender: Gender = "unknown"
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    segment: Optional[str] = None
    device: Optional[str] = None
    locale: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class TotemInteractRequest(BaseModel):
    company_id: str
    session_id: str
    message: str = ""
    profile: Optional[DemographicProfile] = None
    prefer_audio: bool = True
    audio_base64: str | None = None
    input_mode: str | None = None
    message_id: str | None = None


class TotemInteractResponse(BaseModel):
    session_id: str
    language: Language
    text: str
    recommendations: Dict[str, Any]
    audio_base64: Optional[str] = None
    metrics: Dict[str, Any]


class TotemActivateRequest(BaseModel):
    company_id: str
    session_id: str = Field(default="sim-web")
    profile: Optional[Any] = None


class TotemActivateResponse(BaseModel):
    session_id: str
    language: str
    greeting: str
    next: str


class TotemNPSRequest(BaseModel):
    company_id: str
    session_id: str
    score: int
    comment: str | None = None


class TotemNPSResponse(BaseModel):
    ok: bool
    message: str


class TotemTrackRequest(BaseModel):
    company_id: str
    session_id: str
    event: str
    action_id: Optional[str] = None
    action_label: Optional[str] = None
    campaign_id: Optional[str] = None
    turn_index: Optional[int] = None
    message_id: Optional[str] = None
    value: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None


class TotemTrackResponse(BaseModel):
    ok: bool = True
    message: str = "tracked"
