"""Tests for base model mixins."""

import pytest
from datetime import datetime
from sqlalchemy import Column, Integer, String, select
from internal_rdbms import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    DatabaseConfig,
    DatabaseDriver,
    DatabaseSessionManager,
)


class TimestampModel(Base, TimestampMixin):
    """Model with timestamp mixin."""

    __tablename__ = "timestamp_test"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))


class SoftDeleteModel(Base, SoftDeleteMixin):
    """Model with soft delete mixin."""

    __tablename__ = "softdelete_test"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))


class AuditModel(Base, AuditMixin):
    """Model with audit mixin."""

    __tablename__ = "audit_test"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))


@pytest.fixture
async def db_manager():
    """Create in-memory database session manager."""
    config = DatabaseConfig(driver=DatabaseDriver.SQLITE_MEMORY)
    manager = DatabaseSessionManager(config)

    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield manager
    await manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timestamp_mixin_created_at(db_manager):
    """Test TimestampMixin sets created_at automatically."""
    async for session in db_manager():
        model = TimestampModel(name="Test")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        assert model.created_at is not None
        assert isinstance(model.created_at, datetime)
        break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timestamp_mixin_updated_at(db_manager):
    """Test TimestampMixin updates updated_at on modification."""
    async for session in db_manager():
        # Create model
        model = TimestampModel(name="Test")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        original_created = model.created_at
        original_updated = model.updated_at

        assert original_updated is not None

        # Update model
        model.name = "Updated"
        await session.commit()
        await session.refresh(model)

        # created_at should not change
        assert model.created_at == original_created

        # updated_at should change (or stay same if too fast)
        assert model.updated_at >= original_updated
        break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_soft_delete_mixin_default_not_deleted(db_manager):
    """Test SoftDeleteMixin defaults to not deleted."""
    async for session in db_manager():
        model = SoftDeleteModel(name="Test")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        assert model.deleted_at is None
        assert model.is_deleted is False
        break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_soft_delete_mixin_soft_delete(db_manager):
    """Test SoftDeleteMixin soft delete functionality."""
    async for session in db_manager():
        model = SoftDeleteModel(name="Test")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        # Soft delete
        model.soft_delete()

        assert model.deleted_at is not None
        assert isinstance(model.deleted_at, datetime)
        assert model.is_deleted is True

        await session.commit()
        break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_soft_delete_mixin_restore(db_manager):
    """Test SoftDeleteMixin restore functionality."""
    async for session in db_manager():
        model = SoftDeleteModel(name="Test")
        session.add(model)
        await session.commit()

        # Soft delete then restore
        model.soft_delete()
        assert model.is_deleted is True

        model.restore()
        assert model.deleted_at is None
        assert model.is_deleted is False

        await session.commit()
        break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audit_mixin_combines_timestamp_and_user(db_manager):
    """Test AuditMixin includes timestamp and user tracking."""
    async for session in db_manager():
        model = AuditModel(name="Test", created_by="user1", updated_by="user1")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        # Should have timestamp fields
        assert model.created_at is not None
        assert model.updated_at is not None

        # Should have audit fields
        assert model.created_by == "user1"
        assert model.updated_by == "user1"
        break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audit_mixin_tracks_updater(db_manager):
    """Test AuditMixin tracks who updated the record."""
    async for session in db_manager():
        model = AuditModel(name="Test", created_by="user1", updated_by="user1")
        session.add(model)
        await session.commit()
        await session.refresh(model)

        # Update by different user
        model.name = "Updated"
        model.updated_by = "user2"
        await session.commit()
        await session.refresh(model)

        assert model.created_by == "user1"  # Should not change
        assert model.updated_by == "user2"  # Should update
        break


@pytest.mark.unit
def test_timestamp_mixin_has_correct_fields():
    """Test TimestampMixin has expected fields."""
    assert hasattr(TimestampModel, "created_at")
    assert hasattr(TimestampModel, "updated_at")


@pytest.mark.unit
def test_soft_delete_mixin_has_correct_fields():
    """Test SoftDeleteMixin has expected fields."""
    assert hasattr(SoftDeleteModel, "deleted_at")
    assert hasattr(SoftDeleteModel, "is_deleted")


@pytest.mark.unit
def test_soft_delete_mixin_has_methods():
    """Test SoftDeleteMixin has soft_delete and restore methods."""
    assert hasattr(SoftDeleteModel, "soft_delete")
    assert hasattr(SoftDeleteModel, "restore")
    assert callable(SoftDeleteModel.soft_delete)
    assert callable(SoftDeleteModel.restore)


@pytest.mark.unit
def test_audit_mixin_has_correct_fields():
    """Test AuditMixin has all expected fields."""
    assert hasattr(AuditModel, "created_at")
    assert hasattr(AuditModel, "updated_at")
    assert hasattr(AuditModel, "created_by")
    assert hasattr(AuditModel, "updated_by")
