from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy import Date, Time, Boolean, Float

class Executive(Base):
    __tablename__ = "executives"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    photo_url = Column(String(500), nullable=True)
    contact_number = Column(String(15), nullable=True)
    email_address = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    bank_upi = Column(String(255), nullable=True)
    zone = Column(String(100), nullable=True)
    base_location = Column(Text, nullable=True)
    joining_date = Column(Date, nullable=True)

    assignments = relationship("SaarthiSessionAssignment", back_populates="executive")

class DarshanBooking(Base):
    __tablename__ = "darshan_bookings"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    # email_address = Column(String(255), nullable=False)
    contact_number = Column(String(15), nullable=False)
    whatsapp_number = Column(String(15), nullable=False)
    address = Column(Text, nullable=False)
    persons = Column(Integer, nullable=False)
    slot_date = Column(Date, nullable=False)
    slot_time = Column(String(100), nullable=False)
    occupied_units = Column(Integer , nullable=False, default=1)  # New field to track occupied units for the slot
    qr_code = Column(String(500), nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    payment_screenshot = Column(String(255), nullable=False)
    payment_status = Column(String(50), default="partial", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)

    
    sessions = relationship("DarshanSession", back_populates="booking", cascade="all, delete-orphan")
    reviews = relationship("DarshanReview", back_populates="booking", cascade="all, delete-orphan")
    participants = relationship("DarshanParticipant",back_populates="booking",cascade="all, delete-orphan")
    extensions = relationship("SessionExtension", back_populates="booking", cascade="all, delete-orphan")

class DarshanParticipant(Base):
    __tablename__ = "darshan_participants"

    id = Column(Integer, primary_key=True)

    booking_id = Column(
        Integer,
        ForeignKey("darshan_bookings.id", ondelete="CASCADE"),
        nullable=False
    )

    full_name = Column(String(150), nullable=False)
    age = Column(Integer, nullable=False)
    darshan_name = Column(Text, nullable=False)
    is_extension = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    booking = relationship(
        "DarshanBooking",
        back_populates="participants"
    )
class DarshanSession(Base):
    __tablename__ = "darshan_sessions"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("darshan_bookings.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    status = Column(String(50), default="created", nullable=False)

    booking = relationship("DarshanBooking", back_populates="sessions")


class DarshanReview(Base):
    __tablename__ = "darshan_reviews"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("darshan_bookings.id", ondelete="CASCADE"), nullable=False)
    experience_rating = Column(Integer, nullable=False)
    vr_quality_rating = Column(Integer, nullable=False)
    executive_rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    booking = relationship("DarshanBooking", back_populates="reviews")

class SessionExtension(Base):
    __tablename__ = "session_extensions"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("darshan_bookings.id", ondelete="CASCADE"), nullable=False)
    minutes = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    booking = relationship("DarshanBooking", back_populates="extensions")

class SaarthiSessionAssignment(Base):
    __tablename__ = "saarthi_session_assignments"

    id = Column(Integer, primary_key=True, index=True)
    executive_id = Column(Integer, ForeignKey("executives.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("darshan_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="assigned", nullable=False)
    distance_km = Column(Float, nullable=True)
    base_amount = Column(Numeric(10, 2), default=0, nullable=False)
    travel_amount = Column(Numeric(10, 2), default=0, nullable=False)
    extension_amount = Column(Numeric(10, 2), default=0, nullable=False)
    deductions = Column(Numeric(10, 2), default=0, nullable=False)
    net_amount = Column(Numeric(10, 2), default=0, nullable=False)
    extension_minutes = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    executive = relationship("Executive", back_populates="assignments")
    booking = relationship("DarshanBooking")
    

class SaarthiRatingFlag(Base):
    __tablename__ = "saarthi_rating_flags"

    id = Column(Integer, primary_key=True, index=True)
    executive_id = Column(Integer, ForeignKey("executives.id", ondelete="CASCADE"), nullable=False, index=True)
    review_id = Column(Integer, ForeignKey("darshan_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="open", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# class SaarthiIncentiveRule(Base):
#     __tablename__ = "saarthi_incentive_rules"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(150), nullable=False)
#     rule_type = Column(String(50), nullable=False)
#     target_value = Column(Float, nullable=False)
#     amount = Column(Numeric(10, 2), nullable=False)
#     period = Column(String(20), default="monthly", nullable=False)
#     is_active = Column(Boolean, default=True, nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SaarthiPayout(Base):
    __tablename__ = "saarthi_payouts"

    id = Column(Integer, primary_key=True, index=True)
    executive_id = Column(Integer, ForeignKey("executives.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_due = Column(Numeric(10, 2), default=0, nullable=False)
    total_paid = Column(Numeric(10, 2), default=0, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    mode = Column(String(50), nullable=True)
    transaction_ref = Column(String(150), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DistanceRateConfig(Base):
    __tablename__ = "distance_rate_config"

    id = Column(Integer, primary_key=True, index=True)
    base_session_fee = Column(Numeric(10, 2), default=0, nullable=False)
    first_slab_km = Column(Float, default=40, nullable=False)
    first_slab_rate = Column(Numeric(10, 2), default=5, nullable=False)
    overflow_rate = Column(Numeric(10, 2), default=6, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


