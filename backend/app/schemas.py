from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class HCPBase(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    specialty: str | None = None
    organization: str | None = None


class HCPRead(HCPBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class InteractionCreate(BaseModel):
    hcp_name: str = Field(min_length=2, max_length=180)
    occurred_at: datetime
    interaction_type: str = Field(pattern="^(visit|call|email)$")
    products: list[str] = Field(default_factory=list)
    notes: str = Field(min_length=3)
    samples_distributed: str | None = None
    sentiment: str | None = Field(default=None, pattern="^(positive|neutral|negative)$")
    follow_up_action: str | None = None
    follow_up_due_at: datetime | None = None


class InteractionUpdate(BaseModel):
    occurred_at: datetime | None = None
    interaction_type: str | None = Field(default=None, pattern="^(visit|call|email)$")
    products: list[str] | None = None
    notes: str | None = Field(default=None, min_length=3)
    samples_distributed: str | None = None
    sentiment: str | None = Field(default=None, pattern="^(positive|neutral|negative)$")
    follow_up_action: str | None = None


class InteractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    hcp: HCPRead
    occurred_at: datetime
    interaction_type: str
    products: list[str]
    notes: str
    samples_distributed: str | None
    sentiment: str | None
    follow_up_action: str | None
    compliance_flags: list[str]


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=4, max_length=64)
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    action: str
    extracted_data: dict | None = None
    requires_confirmation: bool = False
    records: list[dict] = Field(default_factory=list)


class VoiceSummaryRequest(BaseModel):
    transcript: str = Field(min_length=3, max_length=10000)


class VoiceSummaryResponse(BaseModel):
    summary: str