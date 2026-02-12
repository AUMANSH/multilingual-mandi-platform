"""Create user and vendor models

Revision ID: 001
Revises: 
Create Date: 2024-01-26 14:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('preferred_language', sa.Enum('HINDI', 'ENGLISH', 'TAMIL', 'TELUGU', 'BENGALI', 'MARATHI', 'GUJARATI', 'KANNADA', 'MALAYALAM', 'PUNJABI', name='languagecode'), nullable=False),
        sa.Column('location', sa.Text(), nullable=False),
        sa.Column('tech_literacy_level', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED', name='techliteracylevel'), nullable=False),
        sa.Column('verification_status', sa.Enum('UNVERIFIED', 'PHONE_VERIFIED', 'DOCUMENT_VERIFIED', 'FULLY_VERIFIED', name='verificationstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_active', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_type', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=True)

    # Create vendors table
    op.create_table('vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('business_name', sa.String(length=255), nullable=False),
        sa.Column('business_type', sa.Enum('INDIVIDUAL_TRADER', 'SMALL_BUSINESS', 'COOPERATIVE', 'WHOLESALER', 'RETAILER', 'FARMER', 'MANUFACTURER', name='businesstype'), nullable=False),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('total_transactions', sa.Integer(), nullable=False),
        sa.Column('market_reputation', sa.Enum('NEW', 'DEVELOPING', 'ESTABLISHED', 'TRUSTED', 'PREMIUM', name='marketreputation'), nullable=False),
        sa.Column('is_verified_business', sa.Boolean(), nullable=False),
        sa.Column('business_registration_number', sa.String(length=50), nullable=True),
        sa.Column('specializations', sa.JSON(), nullable=False),
        sa.Column('payment_methods', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('vendors')
    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS languagecode')
    op.execute('DROP TYPE IF EXISTS techliteracylevel')
    op.execute('DROP TYPE IF EXISTS verificationstatus')
    op.execute('DROP TYPE IF EXISTS businesstype')
    op.execute('DROP TYPE IF EXISTS marketreputation')