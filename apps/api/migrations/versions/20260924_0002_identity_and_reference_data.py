"""Identity and reference data: users, auth, showrooms, cities, vehicle taxonomy

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24 11:55:09.804845
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GeoAlchemy2 creates the GiST indexes for Geography columns itself, so this
    # migration does not declare them.
    op.create_table('cities',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('name_ar', sa.String(length=120), nullable=False),
    sa.Column('name_en', sa.String(length=120), nullable=False),
    sa.Column('region_ar', sa.String(length=120), nullable=False),
    sa.Column('region_en', sa.String(length=120), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cities'))
    )
    op.create_index(op.f('ix_cities_slug'), 'cities', ['slug'], unique=True)
    op.create_table('makes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('name_ar', sa.String(length=120), nullable=False),
    sa.Column('name_en', sa.String(length=120), nullable=False),
    sa.Column('aliases', postgresql.ARRAY(sa.String(length=120)), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_makes'))
    )
    op.create_index(op.f('ix_makes_slug'), 'makes', ['slug'], unique=True)
    op.create_table('otp_requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_otp_requests'))
    )
    op.create_index(op.f('ix_otp_requests_phone'), 'otp_requests', ['phone'], unique=False)
    op.create_table('showrooms',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name_ar', sa.String(length=160), nullable=False),
    sa.Column('name_en', sa.String(length=160), nullable=True),
    sa.Column('commercial_registration_number', sa.String(length=20), nullable=False),
    sa.Column('city_id', sa.UUID(), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeogFromText', name='geography'), nullable=True),
    sa.Column('logo_storage_key', sa.String(length=256), nullable=True),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('subscription_tier', sa.Enum('free', 'basic', 'pro', name='subscriptiontier', native_enum=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], name=op.f('fk_showrooms_city_id_cities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_showrooms')),
    sa.UniqueConstraint('commercial_registration_number', name=op.f('uq_showrooms_commercial_registration_number'))
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=True),
    sa.Column('preferred_language', sa.Enum('ar', 'en', name='language', native_enum=False), nullable=False),
    sa.Column('role', sa.Enum('buyer', 'seller', 'showroom_staff', 'admin', name='userrole', native_enum=False), nullable=False),
    sa.Column('city_id', sa.UUID(), nullable=True),
    sa.Column('identity_verified', sa.Boolean(), nullable=False),
    sa.Column('identity_provider', sa.String(length=40), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], name=op.f('fk_users_city_id_cities'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_table('vehicle_models',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('make_id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('name_ar', sa.String(length=120), nullable=False),
    sa.Column('name_en', sa.String(length=120), nullable=False),
    sa.Column('aliases', postgresql.ARRAY(sa.String(length=120)), nullable=False),
    sa.Column('body_type', sa.Enum('sedan', 'suv', 'pickup', 'hatchback', 'coupe', 'van', 'other', name='bodytype', native_enum=False), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['make_id'], ['makes.id'], name=op.f('fk_vehicle_models_make_id_makes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vehicle_models')),
    sa.UniqueConstraint('make_id', 'slug', name='make_slug')
    )
    op.create_index(op.f('ix_vehicle_models_make_id'), 'vehicle_models', ['make_id'], unique=False)
    op.create_index(op.f('ix_vehicle_models_slug'), 'vehicle_models', ['slug'], unique=False)
    op.create_table('refresh_tokens',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('replaced_by_id', sa.UUID(), nullable=True),
    sa.Column('user_agent', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['replaced_by_id'], ['refresh_tokens.id'], name=op.f('fk_refresh_tokens_replaced_by_id_refresh_tokens'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens'))
    )
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_table('showroom_staff',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('showroom_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.Enum('owner', 'manager', 'agent', name='showroomstaffrole', native_enum=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['showroom_id'], ['showrooms.id'], name=op.f('fk_showroom_staff_showroom_id_showrooms'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_showroom_staff_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_showroom_staff')),
    sa.UniqueConstraint('showroom_id', 'user_id', name='showroom_user')
    )
    op.create_index(op.f('ix_showroom_staff_showroom_id'), 'showroom_staff', ['showroom_id'], unique=False)
    op.create_index(op.f('ix_showroom_staff_user_id'), 'showroom_staff', ['user_id'], unique=False)
    op.create_table('trims',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('model_id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('name_ar', sa.String(length=120), nullable=False),
    sa.Column('name_en', sa.String(length=120), nullable=False),
    sa.Column('aliases', postgresql.ARRAY(sa.String(length=120)), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['model_id'], ['vehicle_models.id'], name=op.f('fk_trims_model_id_vehicle_models'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trims')),
    sa.UniqueConstraint('model_id', 'slug', name='model_slug')
    )
    op.create_index(op.f('ix_trims_model_id'), 'trims', ['model_id'], unique=False)
    op.create_index(op.f('ix_trims_slug'), 'trims', ['slug'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trims_slug'), table_name='trims')
    op.drop_index(op.f('ix_trims_model_id'), table_name='trims')
    op.drop_table('trims')
    op.drop_index(op.f('ix_showroom_staff_user_id'), table_name='showroom_staff')
    op.drop_index(op.f('ix_showroom_staff_showroom_id'), table_name='showroom_staff')
    op.drop_table('showroom_staff')
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(op.f('ix_vehicle_models_slug'), table_name='vehicle_models')
    op.drop_index(op.f('ix_vehicle_models_make_id'), table_name='vehicle_models')
    op.drop_table('vehicle_models')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_table('users')
    op.drop_table('showrooms')
    op.drop_index(op.f('ix_otp_requests_phone'), table_name='otp_requests')
    op.drop_table('otp_requests')
    op.drop_index(op.f('ix_makes_slug'), table_name='makes')
    op.drop_table('makes')
    op.drop_index(op.f('ix_cities_slug'), table_name='cities')
    op.drop_table('cities')
