"""Public inspection reports endpoint."""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from ....domain.entities.vehicle import VehicleType
from ....domain.value_objects.checkpoint_types import CheckpointType
from ....infrastructure.services import ServiceFactory

router = APIRouter()


# Response Models
class CheckpointScoreReport(BaseModel):
    """Public checkpoint score information."""
    checkpoint_type: CheckpointType
    score: int
    observations: Optional[str]
    description: str = Field(..., description="Human-readable checkpoint description")

    @classmethod
    def from_checkpoint_score(cls, checkpoint_score):
        """Create from domain CheckpointScore object."""
        return cls(
            checkpoint_type=checkpoint_score.checkpoint_type,
            score=checkpoint_score.score,
            observations=checkpoint_score.observations,
            description=checkpoint_score.checkpoint_type.get_description()
        )


class SafetyResultReport(BaseModel):
    """Public safety result information."""
    total_score: int = Field(..., description="Total score across all checkpoints")
    is_safe: bool = Field(..., description="Whether the vehicle is safe to operate")
    requires_reinspection: bool = Field(..., description="Whether the vehicle requires reinspection")
    safety_category: str = Field(..., description="Safety category: SAFE, CONDITIONAL, or UNSAFE")
    critical_failures: List[CheckpointType] = Field(default_factory=list, description="Checkpoints with critical failures (score < 5)")


class InspectionReport(BaseModel):
    """Public inspection report response."""
    license_plate: str = Field(..., description="Vehicle license plate")
    vehicle_type: VehicleType = Field(..., description="Type of vehicle inspected")
    inspection_date: datetime = Field(..., description="Date when inspection was completed")
    inspector_id: UUID = Field(..., description="ID of the inspector who performed the inspection")

    # Checkpoint scores
    checkpoint_scores: List[CheckpointScoreReport] = Field(..., description="Individual checkpoint scores and observations")

    # Safety assessment
    safety_result: SafetyResultReport = Field(..., description="Overall safety assessment")

    # Additional information
    observations: Optional[str] = Field(None, description="General inspection observations")
    created_at: datetime = Field(..., description="When the inspection was created")
    completed_at: datetime = Field(..., description="When the inspection was completed")

    class Config:
        from_attributes = True


class InspectionNotFoundResponse(BaseModel):
    """Response when no inspection is found."""
    message: str = Field(..., description="Error message")
    license_plate: str = Field(..., description="The searched license plate")
    suggestion: str = Field(..., description="Suggestion for the user")


# Public Endpoints
@router.get("/{license_plate}",
           response_model=InspectionReport,
           responses={
               200: {"description": "Inspection report found"},
               404: {"description": "No inspection found for this license plate", "model": InspectionNotFoundResponse}
           })
async def get_inspection_report(license_plate: str) -> InspectionReport:
    """
    Get the latest inspection report for a vehicle by license plate.

    This is a public endpoint that does not require authentication.
    Returns the most recent completed inspection for the specified license plate.

    Args:
        license_plate: The vehicle's license plate number

    Returns:
        InspectionReport: Complete inspection details including safety assessment

    Raises:
        HTTPException: 404 if no completed inspection is found for the license plate
    """
    try:
        # Clean and validate license plate
        license_plate = license_plate.strip().upper()
        if not license_plate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License plate cannot be empty"
            )

        async with ServiceFactory().get_inspection_service() as inspection_service:
            # Get the latest completed inspection
            inspection = await inspection_service.get_latest_inspection_by_license_plate(license_plate)

            if not inspection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": f"No inspection report found for license plate '{license_plate}'",
                        "license_plate": license_plate,
                        "suggestion": "Please ensure the license plate is correct and that an inspection has been completed for this vehicle."
                    }
                )

            # Only return completed inspections for public access
            if inspection.status.value != "COMPLETED":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": f"No completed inspection found for license plate '{license_plate}'",
                        "license_plate": license_plate,
                        "suggestion": "The inspection for this vehicle may still be in progress. Please check again later."
                    }
                )

            # Convert checkpoint scores to public format
            checkpoint_reports = [
                CheckpointScoreReport.from_checkpoint_score(score)
                for score in inspection.checkpoint_scores
            ]

            # Determine safety category
            safety_category = "SAFE"
            if inspection.requires_reinspection:
                safety_category = "UNSAFE"
            elif not inspection.is_safe:
                safety_category = "CONDITIONAL"

            # Find critical failures (scores < 5)
            critical_failures = [
                score.checkpoint_type for score in inspection.checkpoint_scores
                if score.score < 5
            ]

            # Create safety result report
            safety_result = SafetyResultReport(
                total_score=inspection.total_score,
                is_safe=inspection.is_safe,
                requires_reinspection=inspection.requires_reinspection,
                safety_category=safety_category,
                critical_failures=critical_failures
            )

            # Create the public report
            return InspectionReport(
                license_plate=inspection.license_plate,
                vehicle_type=inspection.vehicle_type,
                inspection_date=inspection.completed_at,
                inspector_id=inspection.inspector_id,
                checkpoint_scores=checkpoint_reports,
                safety_result=safety_result,
                observations=inspection.observations,
                created_at=inspection.created_at,
                completed_at=inspection.completed_at
            )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the error in a real application
        # logger.error(f"Error retrieving inspection report for {license_plate}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the inspection report"
        )


@router.get("/{license_plate}/history",
           response_model=List[InspectionReport],
           responses={
               200: {"description": "Inspection history found"},
               404: {"description": "No inspections found for this license plate"}
           })
async def get_inspection_history(
    license_plate: str,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of inspections to return")
) -> List[InspectionReport]:
    """
    Get inspection history for a vehicle by license plate.

    This is a public endpoint that returns up to the specified number of
    completed inspections for the vehicle, ordered by completion date (most recent first).

    Args:
        license_plate: The vehicle's license plate number
        limit: Maximum number of inspections to return (1-50, default 10)

    Returns:
        List[InspectionReport]: List of inspection reports

    Raises:
        HTTPException: 404 if no completed inspections are found
    """
    try:
        # Clean and validate license plate
        license_plate = license_plate.strip().upper()
        if not license_plate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License plate cannot be empty"
            )

        async with ServiceFactory().get_inspection_service() as inspection_service:
            # Get inspection history
            inspections = await inspection_service.get_inspections_by_license_plate(
                license_plate=license_plate,
                limit=limit
            )

            # Filter only completed inspections for public access
            completed_inspections = [
                inspection for inspection in inspections
                if inspection.status.value == "COMPLETED"
            ]

            if not completed_inspections:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": f"No completed inspection history found for license plate '{license_plate}'",
                        "license_plate": license_plate,
                        "suggestion": "This vehicle may not have any completed inspections on record."
                    }
                )

            # Convert to public report format
            reports = []
            for inspection in completed_inspections:
                # Convert checkpoint scores
                checkpoint_reports = [
                    CheckpointScoreReport.from_checkpoint_score(score)
                    for score in inspection.checkpoint_scores
                ]

                # Determine safety category
                safety_category = "SAFE"
                if inspection.requires_reinspection:
                    safety_category = "UNSAFE"
                elif not inspection.is_safe:
                    safety_category = "CONDITIONAL"

                # Find critical failures
                critical_failures = [
                    score.checkpoint_type for score in inspection.checkpoint_scores
                    if score.score < 5
                ]

                # Create safety result
                safety_result = SafetyResultReport(
                    total_score=inspection.total_score,
                    is_safe=inspection.is_safe,
                    requires_reinspection=inspection.requires_reinspection,
                    safety_category=safety_category,
                    critical_failures=critical_failures
                )

                # Create report
                report = InspectionReport(
                    license_plate=inspection.license_plate,
                    vehicle_type=inspection.vehicle_type,
                    inspection_date=inspection.completed_at,
                    inspector_id=inspection.inspector_id,
                    checkpoint_scores=checkpoint_reports,
                    safety_result=safety_result,
                    observations=inspection.observations,
                    created_at=inspection.created_at,
                    completed_at=inspection.completed_at
                )
                reports.append(report)

            return reports

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the error in a real application
        # logger.error(f"Error retrieving inspection history for {license_plate}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the inspection history"
        )
