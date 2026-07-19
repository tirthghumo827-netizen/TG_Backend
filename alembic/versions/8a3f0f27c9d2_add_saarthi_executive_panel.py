"""add saarthi executive panel

Revision ID: 8a3f0f27c9d2
Revises: 519033f15fbc
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a3f0f27c9d2"
down_revision: Union[str, Sequence[str], None] = "519033f15fbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("executives", sa.Column("photo_url", sa.String(length=500), nullable=True))
    op.add_column("executives", sa.Column("contact_number", sa.String(length=15), nullable=True))
    op.add_column("executives", sa.Column("email_address", sa.String(length=255), nullable=True))
    op.add_column("executives", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("executives", sa.Column("bank_upi", sa.String(length=255), nullable=True))
    op.add_column("executives", sa.Column("zone", sa.String(length=100), nullable=True))
    op.add_column("executives", sa.Column("base_location", sa.Text(), nullable=True))
    op.add_column("executives", sa.Column("joining_date", sa.Date(), nullable=True))

    op.create_table(
        "distance_rate_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_session_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("first_slab_km", sa.Float(), nullable=False, server_default="40"),
        sa.Column("first_slab_rate", sa.Numeric(10, 2), nullable=False, server_default="5"),
        sa.Column("overflow_rate", sa.Numeric(10, 2), nullable=False, server_default="6"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_distance_rate_config_id"), "distance_rate_config", ["id"], unique=False)

    op.create_table(
        "saarthi_incentive_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=False, server_default="monthly"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saarthi_incentive_rules_id"), "saarthi_incentive_rules", ["id"], unique=False)

    op.create_table(
        "saarthi_payouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("executive_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("total_due", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_paid", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("mode", sa.String(length=50), nullable=True),
        sa.Column("transaction_ref", sa.String(length=150), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["executive_id"], ["executives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saarthi_payouts_executive_id"), "saarthi_payouts", ["executive_id"], unique=False)
    op.create_index(op.f("ix_saarthi_payouts_id"), "saarthi_payouts", ["id"], unique=False)

    op.create_table(
        "saarthi_session_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("executive_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="assigned"),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("base_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("travel_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("extension_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("deductions", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("extension_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["darshan_bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["executive_id"], ["executives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saarthi_session_assignments_booking_id"), "saarthi_session_assignments", ["booking_id"], unique=False)
    op.create_index(op.f("ix_saarthi_session_assignments_executive_id"), "saarthi_session_assignments", ["executive_id"], unique=False)
    op.create_index(op.f("ix_saarthi_session_assignments_id"), "saarthi_session_assignments", ["id"], unique=False)

    op.create_table(
        "saarthi_rating_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("executive_id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["executive_id"], ["executives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_id"], ["darshan_reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saarthi_rating_flags_executive_id"), "saarthi_rating_flags", ["executive_id"], unique=False)
    op.create_index(op.f("ix_saarthi_rating_flags_id"), "saarthi_rating_flags", ["id"], unique=False)
    op.create_index(op.f("ix_saarthi_rating_flags_review_id"), "saarthi_rating_flags", ["review_id"], unique=False)

    op.create_table(
        "saarthi_disputes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("executive_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=True),
        sa.Column("payout_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["saarthi_session_assignments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["executive_id"], ["executives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payout_id"], ["saarthi_payouts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saarthi_disputes_executive_id"), "saarthi_disputes", ["executive_id"], unique=False)
    op.create_index(op.f("ix_saarthi_disputes_id"), "saarthi_disputes", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_saarthi_disputes_id"), table_name="saarthi_disputes")
    op.drop_index(op.f("ix_saarthi_disputes_executive_id"), table_name="saarthi_disputes")
    op.drop_table("saarthi_disputes")
    op.drop_index(op.f("ix_saarthi_rating_flags_review_id"), table_name="saarthi_rating_flags")
    op.drop_index(op.f("ix_saarthi_rating_flags_id"), table_name="saarthi_rating_flags")
    op.drop_index(op.f("ix_saarthi_rating_flags_executive_id"), table_name="saarthi_rating_flags")
    op.drop_table("saarthi_rating_flags")
    op.drop_index(op.f("ix_saarthi_session_assignments_id"), table_name="saarthi_session_assignments")
    op.drop_index(op.f("ix_saarthi_session_assignments_executive_id"), table_name="saarthi_session_assignments")
    op.drop_index(op.f("ix_saarthi_session_assignments_booking_id"), table_name="saarthi_session_assignments")
    op.drop_table("saarthi_session_assignments")
    op.drop_index(op.f("ix_saarthi_payouts_id"), table_name="saarthi_payouts")
    op.drop_index(op.f("ix_saarthi_payouts_executive_id"), table_name="saarthi_payouts")
    op.drop_table("saarthi_payouts")
    op.drop_index(op.f("ix_saarthi_incentive_rules_id"), table_name="saarthi_incentive_rules")
    op.drop_table("saarthi_incentive_rules")
    op.drop_index(op.f("ix_distance_rate_config_id"), table_name="distance_rate_config")
    op.drop_table("distance_rate_config")
    op.drop_column("executives", "joining_date")
    op.drop_column("executives", "base_location")
    op.drop_column("executives", "zone")
    op.drop_column("executives", "bank_upi")
    op.drop_column("executives", "address")
    op.drop_column("executives", "email_address")
    op.drop_column("executives", "contact_number")
    op.drop_column("executives", "photo_url")
