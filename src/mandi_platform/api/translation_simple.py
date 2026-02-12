"""
Simplified translation API for testing.
"""

from fastapi import APIRouter

# Initialize router
router = APIRouter(prefix="/api/v1/translation", tags=["translation"])

@router.get("/test")
async def test_endpoint():
    """Test endpoint."""
    return {"message": "test"}