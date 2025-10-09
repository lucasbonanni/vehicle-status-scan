"""Inspection management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from ....domain.entities.inspector import Inspector
from ....domain.entities.vehicle import VehicleType
from ....domain.value_objects.checkpoint_types import CheckpointType
from ....domain.value_objects.checkpoint_score import CheckpointScore
from ....infrastructure.services import ServiceFactory
from ..middleware import get_current_inspector

router = APIRouter()


# Request/Response Models
class CheckpointScoreRequest(BaseModel):
    """Request model for checkpoint scores."""
    checkpoint_type: CheckpointType
    score: int = Field(..., ge=1, le=10, description="Score from 1 to 10")
    observations: Optional[str] = Field(None, max_length=500, description="Optional observations for this checkpoint")


class CreateInspectionRequest(BaseModel):
    """Request model for creating an inspection."""
    license_plate: str = Field(..., min_length=1, max_length=20, description="Vehicle license plate")
    vehicle_type: VehicleType = Field(..., description="Type of vehicle (car or motorcycle)")


class UpdateScoresRequest(BaseModel):
    """Request model for updating checkpoint scores."""
    scores: List[CheckpointScoreRequest] = Field(..., min_items=1, description="List of checkpoint scores to update")


class CompleteInspectionRequest(BaseModel):
    """Request model for completing an inspection."""
    observations: Optional[str] = Field(None, max_length=1000, description="Final inspection observations")


class CheckpointScoreResponse(BaseModel):
    """Response model for checkpoint scores."""
    checkpoint_type: CheckpointType
    score: int
    observations: Optional[str]


class InspectionResponse(BaseModel):
    """Response model for inspection details."""
    id: UUID
    license_plate: str
    vehicle_type: VehicleType
    inspector_id: UUID
    status: str
    scores: List[CheckpointScoreResponse]
    observations: Optional[str]
    total_score: Optional[int]
    is_safe: Optional[bool]
    requires_reinspection: Optional[bool]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class InspectionListResponse(BaseModel):
    """Response model for inspection list."""
    inspections: List[InspectionResponse]
    total: int


# Endpoints
@router.post("/", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    request: CreateInspectionRequest,
    current_inspector: Inspector = Depends(get_current_inspector)
) -> InspectionResponse:
    """
    Create a new inspection.

    Creates a new inspection in draft status for the specified vehicle.
    Requires inspector authentication.
    """
    try:
        async with ServiceFactory().get_inspection_service() as inspection_service:
            inspection = await inspection_service.create_inspection(
                license_plate=request.license_plate,
                vehicle_type=request.vehicle_type,
                inspector_id=str(current_inspector.id)
            )

            # Convert to response model
            return InspectionResponse(
                id=inspection.id,
                license_plate=inspection.license_plate,
                vehicle_type=inspection.vehicle_type,
                inspector_id=inspection.inspector_id,
                status=inspection.status.value,
                scores=[
                    CheckpointScoreResponse(
                        checkpoint_type=score.checkpoint_type,
                        score=score.score,
                        observations=score.observations
                    ) for score in inspection.checkpoint_scores
                ],
                observations=inspection.observations,
                total_score=inspection.total_score,
                is_safe=inspection.is_safe,
                requires_reinspection=inspection.requires_reinspection,
                created_at=inspection.created_at,
                updated_at=inspection.updated_at,
                completed_at=inspection.completed_at
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: UUID,
    current_inspector: Inspector = Depends(get_current_inspector)
) -> InspectionResponse:
    """
    Get inspection details by ID.

    Retrieves detailed information about a specific inspection.
    Requires inspector authentication.
    """
    try:
        async with ServiceFactory().get_inspection_service() as inspection_service:
            inspection = await inspection_service.get_inspection_by_id(str(inspection_id))

            if not inspection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Inspection with ID {inspection_id} not found"
                )

            return InspectionResponse(
                id=inspection.id,
                license_plate=inspection.license_plate,
                vehicle_type=inspection.vehicle_type,
                inspector_id=inspection.inspector_id,
                status=inspection.status.value,
                scores=[
                    CheckpointScoreResponse(
                        checkpoint_type=score.checkpoint_type,
                        score=score.score,
                        observations=score.observations
                    ) for score in inspection.checkpoint_scores
                ],
                observations=inspection.observations,
                total_score=inspection.total_score,
                is_safe=inspection.is_safe,
                requires_reinspection=inspection.requires_reinspection,
                created_at=inspection.created_at,
                updated_at=inspection.updated_at,
                completed_at=inspection.completed_at
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{inspection_id}/scores", response_model=InspectionResponse)
async def update_checkpoint_scores(
    inspection_id: UUID,
    request: UpdateScoresRequest,
    current_inspector: Inspector = Depends(get_current_inspector)
) -> InspectionResponse:
    """
    Update checkpoint scores for an inspection.

    Updates the scores for specified checkpoints in a draft inspection.
    Requires inspector authentication.
    """
    try:
        # Convert request scores to domain objects
        checkpoint_scores = [
            CheckpointScore(
                score=score_req.score,
                checkpoint_type=score_req.checkpoint_type,
                observations=score_req.observations
            )
            for score_req in request.scores
        ]

        async with ServiceFactory().get_inspection_service() as inspection_service:
            inspection = await inspection_service.update_checkpoint_scores(
                inspection_id=str(inspection_id),
                checkpoint_scores=checkpoint_scores
            )

            return InspectionResponse(
                id=inspection.id,
                license_plate=inspection.license_plate,
                vehicle_type=inspection.vehicle_type,
                inspector_id=inspection.inspector_id,
                status=inspection.status.value,
                scores=[
                    CheckpointScoreResponse(
                        checkpoint_type=score.checkpoint_type,
                        score=score.score,
                        observations=score.observations
                    ) for score in inspection.checkpoint_scores
                ],
                observations=inspection.observations,
                total_score=inspection.total_score,
                is_safe=inspection.is_safe,
                requires_reinspection=inspection.requires_reinspection,
                created_at=inspection.created_at,
                updated_at=inspection.updated_at,
                completed_at=inspection.completed_at
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{inspection_id}/complete", response_model=InspectionResponse)
async def complete_inspection(
    inspection_id: UUID,
    request: CompleteInspectionRequest,
    current_inspector: Inspector = Depends(get_current_inspector)
) -> InspectionResponse:
    """
    Complete an inspection.

    Marks an inspection as completed and calculates the final safety result.
    All required checkpoint scores must be provided before completion.
    Requires inspector authentication.
    """
    try:
        async with ServiceFactory().get_inspection_service() as inspection_service:
            inspection = await inspection_service.complete_inspection(
                inspection_id=str(inspection_id),
                observations=request.observations
            )

            return InspectionResponse(
                id=inspection.id,
                license_plate=inspection.license_plate,
                vehicle_type=inspection.vehicle_type,
                inspector_id=inspection.inspector_id,
                status=inspection.status.value,
                scores=[
                    CheckpointScoreResponse(
                        checkpoint_type=score.checkpoint_type,
                        score=score.score,
                        observations=score.observations
                    ) for score in inspection.checkpoint_scores
                ],
                observations=inspection.observations,
                total_score=inspection.total_score,
                is_safe=inspection.is_safe,
                requires_reinspection=inspection.requires_reinspection,
                created_at=inspection.created_at,
                updated_at=inspection.updated_at,
                completed_at=inspection.completed_at
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/", response_model=InspectionListResponse)
async def list_inspections(
    current_inspector: Inspector = Depends(get_current_inspector),
    limit: int = 50
) -> InspectionListResponse:
    """
    List inspections for the current inspector.

    Returns a paginated list of inspections created by the current inspector.
    Requires inspector authentication.
    """
    try:
        async with ServiceFactory().get_inspection_service() as inspection_service:
            inspections = await inspection_service.list_inspections_by_inspector(
                inspector_id=str(current_inspector.id),
                limit=limit
            )

            inspection_responses = [
                InspectionResponse(
                    id=inspection.id,
                    license_plate=inspection.license_plate,
                    vehicle_type=inspection.vehicle_type,
                    inspector_id=inspection.inspector_id,
                    status=inspection.status.value,
                    scores=[
                        CheckpointScoreResponse(
                            checkpoint_type=score.checkpoint_type,
                            score=score.score,
                            observations=score.observations
                        ) for score in inspection.checkpoint_scores
                    ],
                    observations=inspection.observations,
                    total_score=inspection.total_score,
                    is_safe=inspection.is_safe,
                    requires_reinspection=inspection.requires_reinspection,
                    created_at=inspection.created_at,
                    updated_at=inspection.updated_at,
                    completed_at=inspection.completed_at
                ) for inspection in inspections
            ]

            return InspectionListResponse(
                inspections=inspection_responses,
                total=len(inspection_responses)
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
