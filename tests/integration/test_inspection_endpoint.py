"""Integration tests for inspection API endpoints.

Tests the full flow of creating and managing inspections through the API.
"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from httpx import AsyncClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.vehicle_inspection.presentation.api.routes import health, inspections
from src.vehicle_inspection.domain.entities.vehicle import VehicleType
from src.vehicle_inspection.domain.entities.inspection import (
    Inspection,
    InspectionStatus,
)
from src.vehicle_inspection.domain.entities.inspector import (
    Inspector,
    InspectorRole,
    InspectorStatus,
)
from src.vehicle_inspection.domain.value_objects.checkpoint_score import CheckpointScore
from src.vehicle_inspection.domain.value_objects.checkpoint_types import CheckpointType


class TestInspectionEndpoint:
    """Integration tests for inspection API endpoints."""

    @pytest.fixture
    def app(self):
        app = FastAPI(
            title="Vehicle Inspection System - Test",
            description="Test API for vehicle inspections",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )

        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include routes
        app.include_router(health.router, tags=["Health"])
        app.include_router(
            inspections.router, prefix="/api/v1/inspections", tags=["Inspections"]
        )

        return app

    @pytest_asyncio.fixture
    async def async_client(self, app):
        """Create async HTTP client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest_asyncio.fixture
    def mock_inspector(self):
        """Create a mock inspector."""
        return Inspector(
            name="Test Inspector",
            email="inspector@test.com",
            phone="123-456-7890",
            license_number="LIC123",
            inspector_id=uuid4(),
            role=InspectorRole.INSPECTOR,
            status=InspectorStatus.ACTIVE,
            created_at=datetime.utcnow(),
        )

    @pytest_asyncio.fixture
    def mock_jwt_token(self, mock_inspector):
        """Create a mock JWT token."""
        return "mock-jwt-token-for-inspector"

    @pytest.mark.asyncio
    async def test_create_inspection_success(
        self, async_client, mock_inspector, mock_jwt_token
    ):
        """Test successfully creating a new inspection."""

        # Mock the authentication dependency
        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            # Mock the service factory and inspection service
            with patch(
                "src.vehicle_inspection.presentation.api.routes.inspections.get_service_factory"
            ) as mock_factory_func:
                mock_factory = AsyncMock()
                mock_factory_func.return_value = mock_factory

                # Create mock inspection service
                mock_inspection_service = AsyncMock()
                inspection = Inspection(
                    license_plate="ABC123",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                    checkpoint_scores=[],
                    observations="",
                    status=InspectionStatus.DRAFT,
                )
                mock_inspection_service.create_inspection.return_value = inspection

                # Set up the context manager
                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service
                mock_factory.get_inspection_service.return_value.__aexit__.return_value = None

                # Make request
                response = await async_client.post(
                    "/api/v1/inspections/",
                    json={"license_plate": "ABC123", "vehicle_type": "car"},
                    headers={"Authorization": f"Bearer {mock_jwt_token}"},
                )

                # Assert response
                assert response.status_code == 201
                data = response.json()
                assert data["license_plate"] == "ABC123"
                assert data["vehicle_type"] == "car"
                assert data["status"] == "draft"
                assert data["inspector_id"] == str(mock_inspector.id)

    @pytest.mark.asyncio
    async def test_create_inspection_with_invalid_license_plate(
        self, async_client, mock_inspector, mock_jwt_token
    ):
        """Test creating inspection with empty license plate fails."""

        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            with patch(
                "src.vehicle_inspection.presentation.api.routes.inspections.get_service_factory"
            ) as mock_factory_func:
                mock_factory = AsyncMock()
                mock_factory_func.return_value = mock_factory

                # Mock service to raise ValueError for empty license plate
                mock_inspection_service = AsyncMock()
                mock_inspection_service.create_inspection.side_effect = ValueError(
                    "License plate cannot be empty"
                )

                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service
                mock_factory.get_inspection_service.return_value.__aexit__.return_value = None

                # Make request with empty license plate
                response = await async_client.post(
                    "/api/v1/inspections/",
                    json={"license_plate": "", "vehicle_type": "car"},
                    headers={"Authorization": f"Bearer {mock_jwt_token}"},
                )

                # Assert error response
                assert response.status_code == 400
                data = response.json()
                assert "License plate cannot be empty" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_inspection_with_invalid_vehicle_type(
        self, async_client, mock_inspector, mock_jwt_token
    ):
        """Test creating inspection with invalid vehicle type fails."""

        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            # Make request with invalid vehicle type
            response = await async_client.post(
                "/api/v1/inspections/",
                json={"license_plate": "ABC123", "vehicle_type": "invalid_type"},
                headers={"Authorization": f"Bearer {mock_jwt_token}"},
            )

            # Assert error response
            assert response.status_code == 422
            data = response.json()
            assert "validation_error" in data.get("detail", [{}])[0].get("type", "")

    @pytest.mark.asyncio
    async def test_create_inspection_without_authentication(self, async_client):
        """Test creating inspection without authentication fails."""

        response = await async_client.post(
            "/api/v1/inspections/",
            json={"license_plate": "ABC123", "vehicle_type": "car"},
        )

        # Should return 403 Forbidden (no auth header)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_inspection_success(
        self, async_client, mock_inspector, mock_jwt_token
    ):
        """Test successfully retrieving an inspection."""

        inspection_id = uuid4()

        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            with patch(
                "src.vehicle_inspection.presentation.api.routes.inspections.get_service_factory"
            ) as mock_factory_func:
                mock_factory = AsyncMock()
                mock_factory_func.return_value = mock_factory

                # Create mock inspection
                inspection = Inspection(
                    license_plate="ABC123",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                    inspection_id=inspection_id,
                    checkpoint_scores=[],
                    observations="Test observations",
                    status=InspectionStatus.DRAFT,
                )

                mock_inspection_service = AsyncMock()
                mock_inspection_service.get_inspection_by_id.return_value = inspection

                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service
                mock_factory.get_inspection_service.return_value.__aexit__.return_value = None

                # Make request
                response = await async_client.get(
                    f"/api/v1/inspections/{inspection_id}",
                    headers={"Authorization": f"Bearer {mock_jwt_token}"},
                )

                # Assert response
                assert response.status_code == 200
                data = response.json()
                assert data["id"] == str(inspection_id)
                assert data["license_plate"] == "ABC123"
                assert data["observations"] == "Test observations"

    @pytest.mark.asyncio
    async def test_update_inspection_scores(
        self, async_client, mock_inspector, mock_jwt_token
    ):
        """Test updating inspection checkpoint scores."""

        inspection_id = uuid4()

        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            with patch(
                "src.vehicle_inspection.presentation.api.routes.inspections.get_service_factory"
            ) as mock_factory_func:
                mock_factory = AsyncMock()
                mock_factory_func.return_value = mock_factory

                # Create mock inspection with scores
                scores = [
                    CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8, "Good condition"),
                    CheckpointScore(CheckpointType.TIRES, 7, "Minor wear"),
                    CheckpointScore(CheckpointType.STEERING_SYSTEM, 9, "Excellent"),
                    CheckpointScore(CheckpointType.SUSPENSION_SYSTEM, 6, "Acceptable"),
                    CheckpointScore(CheckpointType.LIGHTING_SYSTEM, 8, "Good"),
                    CheckpointScore(CheckpointType.GAS_EMISSIONS, 7, "Acceptable"),
                    CheckpointScore(CheckpointType.ELECTRICAL_SYSTEM, 8, "Good"),
                    CheckpointScore(CheckpointType.BODY_STRUCTURE, 7, "Acceptable"),
                ]

                inspection = Inspection(
                    license_plate="ABC123",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                    inspection_id=inspection_id,
                    checkpoint_scores=scores,
                    observations="Inspection completed",
                    status=InspectionStatus.DRAFT,
                )

                mock_inspection_service = AsyncMock()
                mock_inspection_service.update_checkpoint_scores.return_value = (
                    inspection
                )

                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service
                mock_factory.get_inspection_service.return_value.__aexit__.return_value = None

                # Make request
                response = await async_client.put(
                    f"/api/v1/inspections/{inspection_id}/scores",
                    json={
                        "scores": [
                            {
                                "checkpoint_type": "braking_system",
                                "score": 8,
                                "observations": "Good condition",
                            },
                            {
                                "checkpoint_type": "tires",
                                "score": 7,
                                "observations": "Minor wear",
                            },
                            {
                                "checkpoint_type": "steering_system",
                                "score": 9,
                                "observations": "Excellent",
                            },
                            {
                                "checkpoint_type": "suspension_system",
                                "score": 6,
                                "observations": "Acceptable",
                            },
                            {
                                "checkpoint_type": "lighting_system",
                                "score": 8,
                                "observations": "Good",
                            },
                            {
                                "checkpoint_type": "gas_emissions",
                                "score": 7,
                                "observations": "Acceptable",
                            },
                            {
                                "checkpoint_type": "electrical_system",
                                "score": 8,
                                "observations": "Good",
                            },
                            {
                                "checkpoint_type": "body_structure",
                                "score": 7,
                                "observations": "Acceptable",
                            },
                        ]
                    },
                    headers={"Authorization": f"Bearer {mock_jwt_token}"},
                )

                # Assert response
                assert response.status_code == 200
                data = response.json()
                assert len(data["scores"]) == 8
                assert data["total_score"] == 60  # 8+7+9+6+8+7+8+7 = 60

    @pytest.mark.asyncio
    async def test_complete_inspection(
        self, async_client, mock_inspector, mock_jwt_token
    ):
        """Test completing an inspection."""

        inspection_id = uuid4()

        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            with patch(
                "src.vehicle_inspection.presentation.api.routes.inspections.get_service_factory"
            ) as mock_factory_func:
                mock_factory = AsyncMock()
                mock_factory_func.return_value = mock_factory

                # Create mock completed inspection
                scores = [
                    CheckpointScore(CheckpointType.BRAKING_SYSTEM, 8),
                    CheckpointScore(CheckpointType.TIRES, 9),
                    CheckpointScore(CheckpointType.STEERING_SYSTEM, 8),
                    CheckpointScore(CheckpointType.SUSPENSION_SYSTEM, 7),
                    CheckpointScore(CheckpointType.LIGHTING_SYSTEM, 9),
                    CheckpointScore(CheckpointType.GAS_EMISSIONS, 8),
                    CheckpointScore(CheckpointType.ELECTRICAL_SYSTEM, 8),
                    CheckpointScore(CheckpointType.BODY_STRUCTURE, 8),
                ]

                inspection = Inspection(
                    license_plate="ABC123",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                    inspection_id=inspection_id,
                    checkpoint_scores=scores,
                    observations="Vehicle is safe to operate",
                    status=InspectionStatus.COMPLETED,
                    completed_at=datetime.utcnow(),
                )

                mock_inspection_service = AsyncMock()
                mock_inspection_service.complete_inspection.return_value = inspection

                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service
                mock_factory.get_inspection_service.return_value.__aexit__.return_value = None

                # Make request
                response = await async_client.post(
                    f"/api/v1/inspections/{inspection_id}/complete",
                    json={"observations": "Vehicle is safe to operate"},
                    headers={"Authorization": f"Bearer {mock_jwt_token}"},
                )

                # Assert response
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["is_safe"] is not None
                assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_list_inspections(self, async_client, mock_inspector, mock_jwt_token):
        """Test listing inspections."""

        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            with patch(
                "src.vehicle_inspection.presentation.api.routes.inspections.get_service_factory"
            ) as mock_factory_func:
                mock_factory = AsyncMock()
                mock_factory_func.return_value = mock_factory

                # Create mock inspections
                inspection1 = Inspection(
                    license_plate="ABC123",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                )
                inspection2 = Inspection(
                    license_plate="XYZ789",
                    vehicle_type=VehicleType.MOTORCYCLE,
                    inspector_id=mock_inspector.id,
                )

                mock_inspection_service = AsyncMock()
                mock_inspection_service.get_all_inspections.return_value = [
                    inspection1,
                    inspection2,
                ]

                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service
                mock_factory.get_inspection_service.return_value.__aexit__.return_value = None

                # Make request
                response = await async_client.get(
                    "/api/v1/inspections/",
                    headers={"Authorization": f"Bearer {mock_jwt_token}"},
                )

                # Assert response
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 2
                assert len(data["inspections"]) == 2
                assert data["inspections"][0]["license_plate"] == "ABC123"
                assert data["inspections"][1]["license_plate"] == "XYZ789"


class TestInspectionFullWorkflow:
    """Test the complete inspection workflow."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        app = FastAPI(
            title="Vehicle Inspection System - Test",
            description="Test API for vehicle inspections",
            version="0.1.0",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.include_router(
            inspections.router, prefix="/api/v1/inspections", tags=["Inspections"]
        )

        return app

    @pytest_asyncio.fixture
    async def async_client(self, app):
        """Create async HTTP client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_full_inspection_workflow(self, async_client):
        """Test complete inspection workflow from creation to completion."""

        mock_inspector = Inspector(
            name="Senior Inspector",
            email="senior@test.com",
            phone="555-1234",
            license_number="LIC456",
            inspector_id=uuid4(),
            role=InspectorRole.INSPECTOR,
            status=InspectorStatus.ACTIVE,
        )

        with patch(
            "src.vehicle_inspection.presentation.api.middleware.auth.get_current_inspector"
        ) as mock_auth:
            mock_auth.return_value = mock_inspector

            with patch(
                "src.vehicle_inspection.presentation.api.routes.inspections.get_service_factory"
            ) as mock_factory_func:
                mock_factory = AsyncMock()
                mock_factory_func.return_value = mock_factory

                # Step 1: Create inspection
                print("\n=== Step 1: Creating new inspection ===")
                inspection_id = uuid4()
                inspection = Inspection(
                    license_plate="CAR-2024-01",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                    inspection_id=inspection_id,
                )

                mock_inspection_service = AsyncMock()
                mock_inspection_service.create_inspection.return_value = inspection

                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service
                mock_factory.get_inspection_service.return_value.__aexit__.return_value = None

                response = await async_client.post(
                    "/api/v1/inspections/",
                    json={"license_plate": "CAR-2024-01", "vehicle_type": "car"},
                )

                assert response.status_code == 201
                created_inspection = response.json()
                print(f"✓ Inspection created: {created_inspection['id']}")
                print(f"  License Plate: {created_inspection['license_plate']}")
                print(f"  Status: {created_inspection['status']}")

                # Step 2: Add checkpoint scores
                print("\n=== Step 2: Adding checkpoint scores ===")
                scores_data = [
                    {
                        "checkpoint_type": "braking_system",
                        "score": 8,
                        "observations": "Brake pads in good condition",
                    },
                    {
                        "checkpoint_type": "steering_system",
                        "score": 9,
                        "observations": "Power steering responsive",
                    },
                    {
                        "checkpoint_type": "suspension_system",
                        "score": 7,
                        "observations": "Minor wear on springs",
                    },
                    {
                        "checkpoint_type": "tires",
                        "score": 8,
                        "observations": "Tread depth acceptable",
                    },
                    {
                        "checkpoint_type": "lighting_system",
                        "score": 9,
                        "observations": "All lights functional",
                    },
                    {
                        "checkpoint_type": "gas_emissions",
                        "score": 7,
                        "observations": "Within acceptable range",
                    },
                    {
                        "checkpoint_type": "electrical_system",
                        "score": 8,
                        "observations": "Battery and alternator good",
                    },
                    {
                        "checkpoint_type": "body_structure",
                        "score": 7,
                        "observations": "Minor cosmetic damage",
                    },
                ]

                checkpoint_scores = [
                    CheckpointScore(
                        CheckpointType[score["checkpoint_type"].upper()],
                        score["score"],
                        score["observations"],
                    )
                    for score in scores_data
                ]

                updated_inspection = Inspection(
                    license_plate="CAR-2024-01",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                    inspection_id=inspection_id,
                    checkpoint_scores=checkpoint_scores,
                    status=InspectionStatus.DRAFT,
                )

                mock_inspection_service.update_checkpoint_scores.return_value = (
                    updated_inspection
                )
                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service

                response = await async_client.put(
                    f"/api/v1/inspections/{inspection_id}/scores",
                    json={"scores": scores_data},
                )

                assert response.status_code == 200
                updated = response.json()
                print(f"✓ Scores added: {len(updated['scores'])} checkpoints")
                print(f"  Total Score: {updated['total_score']}/80")
                for score in updated["scores"][:3]:
                    print(f"  - {score['checkpoint_type']}: {score['score']}/10")

                # Step 3: Complete inspection
                print("\n=== Step 3: Completing inspection ===")
                completed_inspection = Inspection(
                    license_plate="CAR-2024-01",
                    vehicle_type=VehicleType.CAR,
                    inspector_id=mock_inspector.id,
                    inspection_id=inspection_id,
                    checkpoint_scores=checkpoint_scores,
                    observations="Vehicle inspection completed. Overall condition is good.",
                    status=InspectionStatus.COMPLETED,
                    completed_at=datetime.utcnow(),
                    is_safe=True,
                    requires_reinspection=False,
                )

                mock_inspection_service.complete_inspection.return_value = (
                    completed_inspection
                )
                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service

                response = await async_client.post(
                    f"/api/v1/inspections/{inspection_id}/complete",
                    json={
                        "observations": "Vehicle inspection completed. Overall condition is good."
                    },
                )

                assert response.status_code == 200
                completed = response.json()
                print("✓ Inspection completed")
                print(f"  Status: {completed['status']}")
                print(f"  Total Score: {completed['total_score']}/80")
                print(f"  Is Safe: {completed['is_safe']}")
                print(f"  Requires Re-inspection: {completed['requires_reinspection']}")
                print(f"  Observations: {completed['observations']}")

                # Step 4: Verify inspection details
                print("\n=== Step 4: Retrieving inspection details ===")
                mock_inspection_service.get_inspection_by_id.return_value = (
                    completed_inspection
                )
                mock_factory.get_inspection_service.return_value.__aenter__.return_value = mock_inspection_service

                response = await async_client.get(
                    f"/api/v1/inspections/{inspection_id}"
                )

                assert response.status_code == 200
                final = response.json()
                print("✓ Inspection retrieved successfully")
                print(f"  ID: {final['id']}")
                print(f"  License Plate: {final['license_plate']}")
                print(f"  Vehicle Type: {final['vehicle_type']}")
                print(f"  Inspector ID: {final['inspector_id']}")
                print(f"  Status: {final['status']}")

                print("\n=== ✓ Full workflow completed successfully ===")
