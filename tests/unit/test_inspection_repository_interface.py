"""Unit tests for InspectionRepository interface."""

import pytest
import inspect
from abc import ABC
from typing import List, Optional
from uuid import UUID, uuid4

from src.vehicle_inspection.application.ports.repositories import InspectionRepository


class TestInspectionRepositoryInterface:
    """Test cases for the InspectionRepository interface."""

    def test_inspection_repository_is_abstract(self):
        """Test that InspectionRepository is properly abstract."""
        # Should inherit from ABC
        assert issubclass(InspectionRepository, ABC)

        # Should be abstract (cannot be instantiated)
        assert inspect.isabstract(InspectionRepository)

        # Should raise TypeError when trying to instantiate
        with pytest.raises(TypeError):
            InspectionRepository()

    def test_inspection_repository_abstract_methods(self):
        """Test that all expected abstract methods are defined."""
        abstract_methods = InspectionRepository.__abstractmethods__

        # Should have exactly 13 abstract methods
        assert len(abstract_methods) == 13

        # Core CRUD methods
        crud_methods = {'save', 'find_by_id', 'update', 'delete', 'exists'}
        assert crud_methods.issubset(abstract_methods)

        # License plate specific methods
        license_plate_methods = {'find_by_license_plate', 'find_latest_by_license_plate', 'count_by_license_plate'}
        assert license_plate_methods.issubset(abstract_methods)

        # Inspector specific methods
        inspector_methods = {'find_by_inspector', 'find_draft_inspections_by_inspector', 'count_by_inspector'}
        assert inspector_methods.issubset(abstract_methods)

        # Status and filtering methods
        filtering_methods = {'find_by_status', 'find_completed_inspections'}
        assert filtering_methods.issubset(abstract_methods)

    def test_save_method_signature(self):
        """Test save method signature."""
        method = getattr(InspectionRepository, 'save')
        sig = inspect.signature(method)

        # Should have self and inspection parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'inspection']

        # Return type should be Inspection
        assert sig.return_annotation == "'Inspection'"

    def test_find_by_id_method_signature(self):
        """Test find_by_id method signature."""
        method = getattr(InspectionRepository, 'find_by_id')
        sig = inspect.signature(method)

        # Should have self and inspection_id parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'inspection_id']

        # inspection_id should be UUID type
        assert sig.parameters['inspection_id'].annotation == UUID

        # Return type should be Optional[Inspection]
        assert 'Optional' in str(sig.return_annotation)

    def test_find_by_license_plate_method_signature(self):
        """Test find_by_license_plate method signature."""
        method = getattr(InspectionRepository, 'find_by_license_plate')
        sig = inspect.signature(method)

        # Should have self and license_plate parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'license_plate']

        # license_plate should be str type
        assert sig.parameters['license_plate'].annotation == str

        # Return type should be List[Inspection]
        assert 'List' in str(sig.return_annotation)

    def test_find_latest_by_license_plate_method_signature(self):
        """Test find_latest_by_license_plate method signature."""
        method = getattr(InspectionRepository, 'find_latest_by_license_plate')
        sig = inspect.signature(method)

        # Should have self and license_plate parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'license_plate']

        # license_plate should be str type
        assert sig.parameters['license_plate'].annotation == str

        # Return type should be Optional[Inspection]
        assert 'Optional' in str(sig.return_annotation)

    def test_find_by_inspector_method_signature(self):
        """Test find_by_inspector method signature."""
        method = getattr(InspectionRepository, 'find_by_inspector')
        sig = inspect.signature(method)

        # Should have self and inspector_id parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'inspector_id']

        # inspector_id should be UUID type
        assert sig.parameters['inspector_id'].annotation == UUID

        # Return type should be List[Inspection]
        assert 'List' in str(sig.return_annotation)

    def test_find_by_status_method_signature(self):
        """Test find_by_status method signature."""
        method = getattr(InspectionRepository, 'find_by_status')
        sig = inspect.signature(method)

        # Should have self and status parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'status']

        # status should be str type
        assert sig.parameters['status'].annotation == str

        # Return type should be List[Inspection]
        assert 'List' in str(sig.return_annotation)

    def test_find_completed_inspections_method_signature(self):
        """Test find_completed_inspections method signature."""
        method = getattr(InspectionRepository, 'find_completed_inspections')
        sig = inspect.signature(method)

        # Should have self and limit parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'limit']

        # limit should be Optional[int] with default None
        limit_param = sig.parameters['limit']
        assert 'Optional' in str(limit_param.annotation)
        assert limit_param.default is None

        # Return type should be List[Inspection]
        assert 'List' in str(sig.return_annotation)

    def test_update_method_signature(self):
        """Test update method signature."""
        method = getattr(InspectionRepository, 'update')
        sig = inspect.signature(method)

        # Should have self and inspection parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'inspection']

        # Return type should be Inspection
        assert sig.return_annotation == "'Inspection'"

    def test_delete_method_signature(self):
        """Test delete method signature."""
        method = getattr(InspectionRepository, 'delete')
        sig = inspect.signature(method)

        # Should have self and inspection_id parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'inspection_id']

        # inspection_id should be UUID type
        assert sig.parameters['inspection_id'].annotation == UUID

        # Return type should be bool
        assert sig.return_annotation == bool

    def test_exists_method_signature(self):
        """Test exists method signature."""
        method = getattr(InspectionRepository, 'exists')
        sig = inspect.signature(method)

        # Should have self and inspection_id parameters
        params = list(sig.parameters.keys())
        assert params == ['self', 'inspection_id']

        # inspection_id should be UUID type
        assert sig.parameters['inspection_id'].annotation == UUID

        # Return type should be bool
        assert sig.return_annotation == bool

    def test_count_methods_signature(self):
        """Test count methods signatures."""
        # Test count_by_inspector
        method = getattr(InspectionRepository, 'count_by_inspector')
        sig = inspect.signature(method)

        params = list(sig.parameters.keys())
        assert params == ['self', 'inspector_id']
        assert sig.parameters['inspector_id'].annotation == UUID
        assert sig.return_annotation == int

        # Test count_by_license_plate
        method = getattr(InspectionRepository, 'count_by_license_plate')
        sig = inspect.signature(method)

        params = list(sig.parameters.keys())
        assert params == ['self', 'license_plate']
        assert sig.parameters['license_plate'].annotation == str
        assert sig.return_annotation == int

    def test_method_docstrings(self):
        """Test that all methods have proper docstrings."""
        abstract_methods = InspectionRepository.__abstractmethods__

        for method_name in abstract_methods:
            method = getattr(InspectionRepository, method_name)
            assert method.__doc__ is not None, f"Method {method_name} missing docstring"
            assert len(method.__doc__.strip()) > 0, f"Method {method_name} has empty docstring"

    def test_interface_consistency(self):
        """Test interface consistency with domain requirements."""
        abstract_methods = InspectionRepository.__abstractmethods__

        # Should support basic entity management
        assert 'save' in abstract_methods
        assert 'find_by_id' in abstract_methods
        assert 'update' in abstract_methods
        assert 'delete' in abstract_methods
        assert 'exists' in abstract_methods

        # Should support license plate queries (key business requirement)
        assert 'find_by_license_plate' in abstract_methods
        assert 'find_latest_by_license_plate' in abstract_methods

        # Should support inspector-based queries
        assert 'find_by_inspector' in abstract_methods
        assert 'find_draft_inspections_by_inspector' in abstract_methods

        # Should support status filtering
        assert 'find_by_status' in abstract_methods
        assert 'find_completed_inspections' in abstract_methods

        # Should provide counting capabilities for statistics
        assert 'count_by_inspector' in abstract_methods
        assert 'count_by_license_plate' in abstract_methods

    def test_cannot_instantiate_concrete_class_without_implementation(self):
        """Test that concrete classes must implement all abstract methods."""

        # Create incomplete implementation
        class IncompleteInspectionRepository(InspectionRepository):
            async def save(self, inspection):
                pass
            # Missing other methods

        # Should not be able to instantiate
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteInspectionRepository()

    def test_complete_implementation_can_be_instantiated(self):
        """Test that complete implementations can be instantiated."""

        # Create complete mock implementation
        class MockInspectionRepository(InspectionRepository):
            async def save(self, inspection): return inspection
            async def find_by_id(self, inspection_id): return None
            async def find_by_license_plate(self, license_plate): return []
            async def find_latest_by_license_plate(self, license_plate): return None
            async def find_by_inspector(self, inspector_id): return []
            async def find_by_status(self, status): return []
            async def find_completed_inspections(self, limit=None): return []
            async def find_draft_inspections_by_inspector(self, inspector_id): return []
            async def update(self, inspection): return inspection
            async def delete(self, inspection_id): return True
            async def exists(self, inspection_id): return False
            async def count_by_inspector(self, inspector_id): return 0
            async def count_by_license_plate(self, license_plate): return 0

        # Should be able to instantiate
        repo = MockInspectionRepository()
        assert repo is not None
        assert isinstance(repo, InspectionRepository)
