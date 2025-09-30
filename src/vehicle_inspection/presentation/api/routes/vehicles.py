"""Vehicle endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_vehicles() -> dict[str, str]:
    """List all vehicles (placeholder)."""
    return {"message": "Vehicle endpoints - coming soon"}


@router.post("/")
async def create_vehicle() -> dict[str, str]:
    """Create new vehicle (placeholder)."""
    return {"message": "Create vehicle - coming soon"}


@router.get("/{license_plate}")
async def get_vehicle(license_plate: str) -> dict[str, str]:
    """Get vehicle by license plate (placeholder)."""
    return {"message": f"Get vehicle {license_plate} - coming soon"}
