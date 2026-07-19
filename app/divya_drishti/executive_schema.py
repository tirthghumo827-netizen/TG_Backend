from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExecutiveProfileUpdate(BaseModel):
    photo_url: Optional[str] = None
    contact_number: Optional[str] = Field(None, max_length=15)
    email_address: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    bank_upi: Optional[str] = Field(None, max_length=255)


class ExecutiveProfileResponse(BaseModel):
    id: int
    full_name: str
    photo_url: Optional[str] = None
    contact_number: Optional[str] = None
    email_address: Optional[str] = None
    address: Optional[str] = None
    bank_upi: Optional[str] = None
    zone: Optional[str] = None
    base_location: Optional[str] = None
    joining_date: Optional[date] = None

    class Config:
        from_attributes = True


class SessionAssignmentResponse(BaseModel):
    id: int
    booking_id: int
    status: str
    scheduled_date: Optional[date] = None
    scheduled_time: Optional[str] = None
    customer_name: str
    customer_contact: Optional[str] = None
    address_area: Optional[str] = None
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    extension_minutes: int
    notes: Optional[str] = None
    base_amount: float
    travel_amount: float
    extension_amount: float
    deductions: float
    net_amount: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SessionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(confirmed|started|completed|cancelled)$")
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    distance_km: Optional[float] = Field(None, ge=0)
    deductions: Optional[float] = Field(None, ge=0)


class SessionExtensionLog(BaseModel):
    minutes: int = Field(..., gt=0)
    amount: float = Field(..., ge=0)


class SessionNotesUpdate(BaseModel):
    notes: str = Field(..., min_length=1)


class RatingReviewResponse(BaseModel):
    review_id: int
    booking_id: int
    score: int
    experience_rating: int
    vr_quality_rating: int
    comment: Optional[str] = None
    created_at: datetime
    flagged: bool = False


class RatingFlagCreate(BaseModel):
    reason: str = Field(..., min_length=3)


# class IncentiveProgressResponse(BaseModel):
#     rule_id: int
#     name: str
#     rule_type: str
#     period: str
#     target_value: float
#     current_value: float
#     amount: float
#     achieved: bool


class EarningsSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    sessions_completed: int
    total_distance_km: float
    total_base_amount: float
    total_travel_amount: float
    total_extension_amount: float
    total_deductions: float
    total_session_earnings: float
    settled_amount: float
    due_amount: float
    average_rating: Optional[float] = None


class DashboardResponse(BaseModel):
    today_sessions: int
    week_earnings: float
    current_rating: Optional[float] = None
    pending_due_amount: float
    # active_incentives: list[IncentiveProgressResponse]


class PayoutResponse(BaseModel):
    id: int
    period_start: date
    period_end: date
    total_due: float
    total_paid: float
    status: str
    mode: Optional[str] = None
    transaction_ref: Optional[str] = None
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BookingApprovalRequest(BaseModel):
    executive_id: int
