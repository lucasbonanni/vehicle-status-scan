"""Unit tests for Alembic migration 003_add_inspections."""

import pytest
import importlib.util
from pathlib import Path


class TestInspectionsMigration:
    """Test cases for the inspections table migration."""

    @classmethod
    def setup_class(cls):
        """Load the migration module for testing."""
        migration_path = Path(__file__).parent.parent.parent / "alembic" / "versions" / "003_add_inspections.py"

        spec = importlib.util.spec_from_file_location("migration_003", migration_path)
        cls.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.migration)

    def test_migration_metadata(self):
        """Test migration metadata is correctly set."""
        assert self.migration.revision == '003_add_inspections'
        assert self.migration.down_revision == '002_add_inspectors'
        assert self.migration.branch_labels is None
        assert self.migration.depends_on is None

    def test_migration_functions_exist(self):
        """Test that upgrade and downgrade functions exist."""
        assert hasattr(self.migration, 'upgrade')
        assert hasattr(self.migration, 'downgrade')
        assert callable(self.migration.upgrade)
        assert callable(self.migration.downgrade)

    def test_migration_structure(self):
        """Test migration structure and documentation."""
        # Check that the migration file has the expected docstring
        assert self.migration.__doc__ is not None
        assert "Add inspections table" in self.migration.__doc__

        # Check revision chain is correct
        assert self.migration.down_revision == '002_add_inspectors'

    def test_migration_imports(self):
        """Test that all required imports are present."""
        import inspect

        # Get the source code of the migration file
        source = inspect.getsource(self.migration)

        # Check for required imports
        assert 'from alembic import op' in source
        assert 'import sqlalchemy as sa' in source
        assert 'from sqlalchemy.dialects import postgresql' in source

    def test_enum_creation_in_upgrade(self):
        """Test that enum types are created in upgrade."""
        import inspect

        upgrade_source = inspect.getsource(self.migration.upgrade)

        # Check that enum types are created
        assert "CREATE TYPE vehicletype" in upgrade_source
        assert "CREATE TYPE inspectionstatus" in upgrade_source
        assert "('car', 'motorcycle')" in upgrade_source
        assert "('draft', 'completed')" in upgrade_source

    def test_table_creation_in_upgrade(self):
        """Test that inspections table is created in upgrade."""
        import inspect

        upgrade_source = inspect.getsource(self.migration.upgrade)

        # Check that table is created
        assert "op.create_table('inspections'" in upgrade_source

        # Check for key columns
        assert "license_plate" in upgrade_source
        assert "vehicle_type" in upgrade_source
        assert "inspector_id" in upgrade_source
        assert "checkpoint_scores" in upgrade_source
        assert "total_score" in upgrade_source
        assert "is_safe" in upgrade_source
        assert "observations" in upgrade_source
        assert "status" in upgrade_source

    def test_indexes_creation_in_upgrade(self):
        """Test that indexes are created in upgrade."""
        import inspect

        upgrade_source = inspect.getsource(self.migration.upgrade)

        # Check that indexes are created
        assert "ix_inspections_license_plate" in upgrade_source
        assert "ix_inspections_inspector_id" in upgrade_source
        assert "ix_inspections_created_at" in upgrade_source
        assert "ix_inspections_status" in upgrade_source

    def test_foreign_key_in_upgrade(self):
        """Test that foreign key constraint is created in upgrade."""
        import inspect

        upgrade_source = inspect.getsource(self.migration.upgrade)

        # Check that foreign key constraint is created
        assert "ForeignKeyConstraint" in upgrade_source
        assert "inspector_id" in upgrade_source
        assert "inspectors.id" in upgrade_source

    def test_downgrade_cleanup(self):
        """Test that downgrade properly cleans up all created objects."""
        import inspect

        downgrade_source = inspect.getsource(self.migration.downgrade)

        # Check that indexes are dropped
        assert "drop_index" in downgrade_source
        assert "ix_inspections_license_plate" in downgrade_source
        assert "ix_inspections_inspector_id" in downgrade_source
        assert "ix_inspections_created_at" in downgrade_source
        assert "ix_inspections_status" in downgrade_source

        # Check that table is dropped
        assert "drop_table('inspections')" in downgrade_source

        # Check that enum types are dropped
        assert "DROP TYPE inspectionstatus" in downgrade_source
        assert "DROP TYPE vehicletype" in downgrade_source

    def test_migration_order(self):
        """Test that migration operations are in correct order."""
        import inspect

        upgrade_source = inspect.getsource(self.migration.upgrade)
        downgrade_source = inspect.getsource(self.migration.downgrade)

        # In upgrade: enums first, then table, then indexes
        enum_pos = upgrade_source.find("CREATE TYPE")
        table_pos = upgrade_source.find("create_table")
        index_pos = upgrade_source.find("create_index")

        assert enum_pos < table_pos < index_pos

        # In downgrade: reverse order - indexes first, then table, then enums
        index_drop_pos = downgrade_source.find("drop_index")
        table_drop_pos = downgrade_source.find("drop_table")
        enum_drop_pos = downgrade_source.find("DROP TYPE")

        assert index_drop_pos < table_drop_pos < enum_drop_pos

    def test_column_definitions(self):
        """Test that column definitions match expected schema."""
        import inspect

        upgrade_source = inspect.getsource(self.migration.upgrade)

        # Test key column definitions
        assert "postgresql.UUID(as_uuid=True)" in upgrade_source
        assert "sa.String(length=20)" in upgrade_source  # license_plate
        assert "postgresql.JSON" in upgrade_source  # checkpoint_scores
        assert "sa.Numeric(precision=5, scale=2)" in upgrade_source  # total_score
        assert "sa.Boolean()" in upgrade_source  # is_safe, requires_reinspection
        assert "sa.Text()" in upgrade_source  # observations
        assert "sa.DateTime()" in upgrade_source  # timestamps
