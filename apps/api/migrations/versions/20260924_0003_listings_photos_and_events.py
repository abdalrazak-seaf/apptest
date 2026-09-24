"""Listings, photos and analytics events

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24 16:27:28.296661
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GeoAlchemy2 creates the GiST index for the Geography column itself.
    op.create_table('listings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('seller_id', sa.UUID(), nullable=False),
    sa.Column('showroom_id', sa.UUID(), nullable=True),
    sa.Column('seller_type', sa.Enum('private', 'showroom', name='sellertype', native_enum=False), nullable=False),
    sa.Column('make_id', sa.UUID(), nullable=False),
    sa.Column('model_id', sa.UUID(), nullable=False),
    sa.Column('trim_id', sa.UUID(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('mileage_km', sa.Integer(), nullable=False),
    sa.Column('body_type', sa.Enum('sedan', 'suv', 'pickup', 'hatchback', 'coupe', 'van', 'other', name='bodytype', native_enum=False), nullable=True),
    sa.Column('transmission', sa.Enum('automatic', 'manual', name='transmission', native_enum=False), nullable=False),
    sa.Column('fuel_type', sa.Enum('petrol', 'diesel', 'hybrid', 'electric', name='fueltype', native_enum=False), nullable=False),
    sa.Column('engine', sa.String(length=60), nullable=True),
    sa.Column('color_ar', sa.String(length=40), nullable=True),
    sa.Column('regional_spec', sa.Enum('saudi', 'gcc', 'american', 'other', name='regionalspec', native_enum=False), nullable=False),
    sa.Column('accident_history_declared', sa.Boolean(), nullable=False),
    sa.Column('service_history_declared', sa.Boolean(), nullable=False),
    sa.Column('asking_price_sar', sa.Integer(), nullable=False),
    sa.Column('floor_price_sar', sa.Integer(), nullable=True),
    sa.Column('negotiable', sa.Boolean(), nullable=False),
    sa.Column('city_id', sa.UUID(), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeogFromText', name='geography'), nullable=True),
    sa.Column('description_ar', sa.Text(), nullable=True),
    sa.Column('description_en', sa.Text(), nullable=True),
    sa.Column('search_text', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'pending_review', 'active', 'hidden', 'rejected', 'sold', 'expired', name='listingstatus', native_enum=False), nullable=False),
    sa.Column('status_reason_code', sa.Enum('seller_draft', 'seller_hid', 'seller_sold', 'seller_republished', 'awaiting_review', 'approved', 'missing_photos', 'incomplete_details', 'suspected_duplicate', 'price_anomaly', 'prohibited_content', 'contact_in_description', 'suspected_fraud', 'expired_unsold', name='statusreasoncode', native_enum=False), nullable=True),
    sa.Column('status_reason_note', sa.String(length=500), nullable=True),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sold_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('final_price_sar', sa.Integer(), nullable=True),
    sa.Column('views_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('asking_price_sar > 0', name=op.f('ck_listings_asking_price_positive')),
    sa.CheckConstraint('floor_price_sar IS NULL OR floor_price_sar > 0', name=op.f('ck_listings_floor_price_positive')),
    sa.CheckConstraint('mileage_km >= 0', name=op.f('ck_listings_mileage_non_negative')),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], name=op.f('fk_listings_city_id_cities'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['make_id'], ['makes.id'], name=op.f('fk_listings_make_id_makes'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['model_id'], ['vehicle_models.id'], name=op.f('fk_listings_model_id_vehicle_models'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['seller_id'], ['users.id'], name=op.f('fk_listings_seller_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['showroom_id'], ['showrooms.id'], name=op.f('fk_listings_showroom_id_showrooms'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['trim_id'], ['trims.id'], name=op.f('fk_listings_trim_id_trims'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_listings'))
    )
    op.create_index(op.f('ix_listings_city_id'), 'listings', ['city_id'], unique=False)
    op.create_index(op.f('ix_listings_seller_id'), 'listings', ['seller_id'], unique=False)
    op.create_index(op.f('ix_listings_showroom_id'), 'listings', ['showroom_id'], unique=False)
    op.create_index(op.f('ix_listings_status'), 'listings', ['status'], unique=False)
    op.create_index('ix_listings_status_city_created', 'listings', ['status', 'city_id', 'created_at'], unique=False)
    op.create_index('ix_listings_status_price', 'listings', ['status', 'asking_price_sar'], unique=False)
    op.create_table('events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('listing_id', sa.UUID(), nullable=True),
    sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], name=op.f('fk_events_listing_id_listings'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_events_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_events'))
    )
    op.create_index(op.f('ix_events_listing_id'), 'events', ['listing_id'], unique=False)
    op.create_index('ix_events_name_created', 'events', ['name', 'created_at'], unique=False)
    op.create_index(op.f('ix_events_user_id'), 'events', ['user_id'], unique=False)
    op.create_table('listing_photos',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('listing_id', sa.UUID(), nullable=False),
    sa.Column('storage_key', sa.String(length=256), nullable=False),
    sa.Column('content_type', sa.String(length=40), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('perceptual_hash', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], name=op.f('fk_listing_photos_listing_id_listings'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_listing_photos')),
    sa.UniqueConstraint('listing_id', 'position', name='listing_position')
    )
    op.create_index(op.f('ix_listing_photos_listing_id'), 'listing_photos', ['listing_id'], unique=False)
    op.create_index(op.f('ix_listing_photos_perceptual_hash'), 'listing_photos', ['perceptual_hash'], unique=False)
    op.create_table('listing_status_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('listing_id', sa.UUID(), nullable=False),
    sa.Column('from_status', sa.Enum('draft', 'pending_review', 'active', 'hidden', 'rejected', 'sold', 'expired', name='listingstatus', native_enum=False), nullable=True),
    sa.Column('to_status', sa.Enum('draft', 'pending_review', 'active', 'hidden', 'rejected', 'sold', 'expired', name='listingstatus', native_enum=False), nullable=False),
    sa.Column('reason_code', sa.Enum('seller_draft', 'seller_hid', 'seller_sold', 'seller_republished', 'awaiting_review', 'approved', 'missing_photos', 'incomplete_details', 'suspected_duplicate', 'price_anomaly', 'prohibited_content', 'contact_in_description', 'suspected_fraud', 'expired_unsold', name='statusreasoncode', native_enum=False), nullable=True),
    sa.Column('note', sa.String(length=500), nullable=True),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_listing_status_events_actor_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], name=op.f('fk_listing_status_events_listing_id_listings'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_listing_status_events'))
    )
    op.create_index(op.f('ix_listing_status_events_listing_id'), 'listing_status_events', ['listing_id'], unique=False)


    op.create_index(
        "ix_listings_search_text_trgm",
        "listings",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_listings_search_text_trgm", table_name="listings")
    op.drop_index(op.f('ix_listing_status_events_listing_id'), table_name='listing_status_events')
    op.drop_table('listing_status_events')
    op.drop_index(op.f('ix_listing_photos_perceptual_hash'), table_name='listing_photos')
    op.drop_index(op.f('ix_listing_photos_listing_id'), table_name='listing_photos')
    op.drop_table('listing_photos')
    op.drop_index(op.f('ix_events_user_id'), table_name='events')
    op.drop_index('ix_events_name_created', table_name='events')
    op.drop_index(op.f('ix_events_listing_id'), table_name='events')
    op.drop_table('events')
    op.drop_index('ix_listings_status_price', table_name='listings')
    op.drop_index('ix_listings_status_city_created', table_name='listings')
    op.drop_index(op.f('ix_listings_status'), table_name='listings')
    op.drop_index(op.f('ix_listings_showroom_id'), table_name='listings')
    op.drop_index(op.f('ix_listings_seller_id'), table_name='listings')
    op.drop_index(op.f('ix_listings_city_id'), table_name='listings')
    op.drop_table('listings')
