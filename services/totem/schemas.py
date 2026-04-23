from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


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
    prefer_audio: bool = True


class TotemActivateResponse(BaseModel):
    session_id: str
    language: str
    greeting: str
    next: str
    audio_base64: Optional[str] = None
    audio_provider: Optional[str] = None


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


class TotemLeadCaptureRequest(BaseModel):
    company_id: str
    session_id: str
    full_name: str = Field(..., min_length=3)
    age: int = Field(..., ge=0, le=120)
    gender: Gender
    email: EmailStr
    cpf: str = Field(..., min_length=11)
    favorite_brands: list[str] = Field(default_factory=list)
    lgpd_consent: bool
    source: str = "totem_live"

    newsletter_opt_in: bool = True
    consent_version: str = "lgpd-v1"
    consent_text: str = (
        "Autorizo o tratamento dos meus dados para acesso às ofertas, "
        "newsletter e recuperação resumida do atendimento."
    )

    research_summary: str | None = None
    recommendations_snapshot: Dict[str, Any] = Field(default_factory=dict)

    ip_address: str | None = None
    user_agent: str | None = None


class TotemLeadCaptureResponse(BaseModel):
    ok: bool
    message: str
    lead_id: str | None = None
    access_qr_url: str | None = None
    recovery_qr_url: str | None = None
