"""Add product models and categories

Revision ID: 003_add_product_models
Revises: 002_add_user_models
Create Date: 2026-01-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_product_models'
down_revision = '002_add_user_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_categories table
    op.create_table('product_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_enum', sa.Enum('GRAINS', 'VEGETABLES', 'FRUITS', 'SPICES', 'DAIRY', 'MEAT', 'SEAFOOD', 'PULSES', 'OILS', 'TEXTILES', 'HANDICRAFTS', 'ELECTRONICS', 'TOOLS', 'HOUSEHOLD', 'OTHER', name='productcategory'), nullable=False),
        sa.Column('names', sa.JSON(), nullable=False),
        sa.Column('descriptions', sa.JSON(), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['product_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_enum')
    )

    # Create products table
    op.create_table('products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('names', sa.JSON(), nullable=False),
        sa.Column('descriptions', sa.JSON(), nullable=False),
        sa.Column('base_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('unit', sa.Enum('KILOGRAM', 'GRAM', 'QUINTAL', 'TON', 'LITER', 'MILLILITER', 'PIECE', 'DOZEN', 'BUNDLE', 'BAG', 'BOX', 'MAUND', 'SER', 'TOLA', 'BIGHA', 'ACRE', name='measurementunit'), nullable=False),
        sa.Column('minimum_order_quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('maximum_order_quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('quality_grade', sa.Enum('PREMIUM', 'STANDARD', 'ECONOMY', 'ORGANIC', 'FAIR_TRADE', name='qualitygrade'), nullable=False),
        sa.Column('condition', sa.Enum('NEW', 'LIKE_NEW', 'GOOD', 'FAIR', 'REFURBISHED', name='productcondition'), nullable=False),
        sa.Column('availability_status', sa.Enum('AVAILABLE', 'LIMITED_STOCK', 'OUT_OF_STOCK', 'SEASONAL', 'DISCONTINUED', 'PRE_ORDER', name='availabilitystatus'), nullable=False),
        sa.Column('stock_quantity', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('seasonal_pattern', sa.Enum('YEAR_ROUND', 'SUMMER', 'MONSOON', 'WINTER', 'SPRING', 'HARVEST_SEASON', 'FESTIVAL_SEASON', name='seasonalpattern'), nullable=False),
        sa.Column('location', sa.JSON(), nullable=False),
        sa.Column('images', sa.JSON(), nullable=False),
        sa.Column('videos', sa.JSON(), nullable=False),
        sa.Column('attributes', sa.JSON(), nullable=False),
        sa.Column('search_keywords', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('elasticsearch_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('elasticsearch_sync_version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['product_categories.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku')
    )

    # Create price_history table
    op.create_table('price_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('quality_grade', sa.Enum('PREMIUM', 'STANDARD', 'ECONOMY', 'ORGANIC', 'FAIR_TRADE', name='qualitygrade'), nullable=False),
        sa.Column('location', sa.JSON(), nullable=False),
        sa.Column('source', sa.Enum('VENDOR_LISTED', 'MARKET_API', 'GOVERNMENT_DATA', 'HISTORICAL_AVERAGE', 'ML_PREDICTION', name='pricesource'), nullable=False),
        sa.Column('market_conditions', sa.Enum('NORMAL', 'HIGH_DEMAND', 'LOW_DEMAND', 'SUPPLY_SHORTAGE', 'OVERSUPPLY', 'SEASONAL_PEAK', 'FESTIVAL_RUSH', name='marketconditions'), nullable=False),
        sa.Column('quantity_range', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_product_vendor_category', 'products', ['vendor_id', 'category_id'])
    op.create_index('idx_product_availability', 'products', ['availability_status', 'is_active'])
    op.create_index('idx_product_price_range', 'products', ['base_price', 'quality_grade'])
    op.create_index('idx_product_location', 'products', ['location'], postgresql_using='gin')
    op.create_index('idx_product_search', 'products', ['search_keywords'], postgresql_using='gin')
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'])
    
    op.create_index('idx_price_history_product_date', 'price_history', ['product_id', 'recorded_at'])
    op.create_index('idx_price_history_location_date', 'price_history', ['location', 'recorded_at'], postgresql_using='gin')
    op.create_index('idx_price_history_source', 'price_history', ['source', 'recorded_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_price_history_source', table_name='price_history')
    op.drop_index('idx_price_history_location_date', table_name='price_history')
    op.drop_index('idx_price_history_product_date', table_name='price_history')
    
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_index('idx_product_search', table_name='products')
    op.drop_index('idx_product_location', table_name='products')
    op.drop_index('idx_product_price_range', table_name='products')
    op.drop_index('idx_product_availability', table_name='products')
    op.drop_index('idx_product_vendor_category', table_name='products')

    # Drop tables
    op.drop_table('price_history')
    op.drop_table('products')
    op.drop_table('product_categories')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS marketconditions')
    op.execute('DROP TYPE IF EXISTS pricesource')
    op.execute('DROP TYPE IF EXISTS seasonalpattern')
    op.execute('DROP TYPE IF EXISTS availabilitystatus')
    op.execute('DROP TYPE IF EXISTS productcondition')
    op.execute('DROP TYPE IF EXISTS measurementunit')
    op.execute('DROP TYPE IF EXISTS productcategory')