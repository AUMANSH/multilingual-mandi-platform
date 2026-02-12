"""Minimal translation API test."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/translation", tags=["translation"])

@router.get("/test")
async def test_endpoint():
    return {"message": "test"}