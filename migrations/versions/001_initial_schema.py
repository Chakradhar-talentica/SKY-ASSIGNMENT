"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2026-03-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create flights table
    op.create_table(
        'flights',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flight_number', sa.String(10), nullable=False),
        sa.Column('departure_airport', sa.String(3), nullable=False),
        sa.Column('arrival_airport', sa.String(3), nullable=False),
        sa.Column('departure_time', sa.DateTime(), nullable=False),
        sa.Column('arrival_time', sa.DateTime(), nullable=False),
        sa.Column('aircraft_type', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_flights'))
    )
    op.create_index(op.f('ix_flights_flight_number'), 'flights', ['flight_number'], unique=False)

    # Create passengers table
    op.create_table(
        'passengers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('booking_reference', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_passengers')),
        sa.UniqueConstraint('email', name=op.f('uq_passengers_email'))
    )
    op.create_index(op.f('ix_passengers_email'), 'passengers', ['email'], unique=True)
    op.create_index(op.f('ix_passengers_booking_reference'), 'passengers', ['booking_reference'], unique=False)

    # Create seats table
    op.create_table(
        'seats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flight_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seat_number', sa.String(4), nullable=False),
        sa.Column('seat_class', sa.String(20), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('held_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('held_at', sa.DateTime(), nullable=True),
        sa.Column('hold_expires_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id'], name=op.f('fk_seats_flight_id_flights')),
        sa.ForeignKeyConstraint(['held_by'], ['passengers.id'], name=op.f('fk_seats_held_by_passengers')),
        sa.ForeignKeyConstraint(['confirmed_by'], ['passengers.id'], name=op.f('fk_seats_confirmed_by_passengers')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_seats'))
    )
    op.create_index('idx_seats_flight_id', 'seats', ['flight_id'], unique=False)
    op.create_index('idx_seats_status', 'seats', ['status'], unique=False)
    op.create_index('idx_seats_flight_status', 'seats', ['flight_id', 'status'], unique=False)

    # Create seat_state_history table
    op.create_table(
        'seat_state_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('previous_status', sa.String(20), nullable=True),
        sa.Column('new_status', sa.String(20), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('change_reason', sa.String(100), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['seat_id'], ['seats.id'], name=op.f('fk_seat_state_history_seat_id_seats')),
        sa.ForeignKeyConstraint(['changed_by'], ['passengers.id'], name=op.f('fk_seat_state_history_changed_by_passengers')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_seat_state_history'))
    )
    op.create_index('idx_seat_history_seat_id', 'seat_state_history', ['seat_id'], unique=False)
    op.create_index('idx_seat_history_changed_at', 'seat_state_history', ['changed_at'], unique=False)

    # Create checkins table
    op.create_table(
        'checkins',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('passenger_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('flight_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seat_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['flight_id'], ['flights.id'], name=op.f('fk_checkins_flight_id_flights')),
        sa.ForeignKeyConstraint(['passenger_id'], ['passengers.id'], name=op.f('fk_checkins_passenger_id_passengers')),
        sa.ForeignKeyConstraint(['seat_id'], ['seats.id'], name=op.f('fk_checkins_seat_id_seats')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_checkins'))
    )
    op.create_index('idx_checkin_passenger_flight', 'checkins', ['passenger_id', 'flight_id'], unique=True)
    op.create_index('idx_checkin_status', 'checkins', ['status'], unique=False)

    # Create baggage table
    op.create_table(
        'baggage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('checkin_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('excess_fee', sa.Float(), nullable=True),
        sa.Column('fee_paid', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['checkin_id'], ['checkins.id'], name=op.f('fk_baggage_checkin_id_checkins')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_baggage'))
    )

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('checkin_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['checkin_id'], ['checkins.id'], name=op.f('fk_payments_checkin_id_checkins')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_payments'))
    )


def downgrade() -> None:
    op.drop_table('payments')
    op.drop_table('baggage')
    op.drop_index('idx_checkin_status', table_name='checkins')
    op.drop_index('idx_checkin_passenger_flight', table_name='checkins')
    op.drop_table('checkins')
    op.drop_index('idx_seat_history_changed_at', table_name='seat_state_history')
    op.drop_index('idx_seat_history_seat_id', table_name='seat_state_history')
    op.drop_table('seat_state_history')
    op.drop_index('idx_seats_flight_status', table_name='seats')
    op.drop_index('idx_seats_status', table_name='seats')
    op.drop_index('idx_seats_flight_id', table_name='seats')
    op.drop_table('seats')
    op.drop_index(op.f('ix_passengers_booking_reference'), table_name='passengers')
    op.drop_index(op.f('ix_passengers_email'), table_name='passengers')
    op.drop_table('passengers')
    op.drop_index(op.f('ix_flights_flight_number'), table_name='flights')
    op.drop_table('flights')

