"""
Unit tests for abstract storage interface (T032).

Tests exception hierarchy and abstract method enforcement.
"""

import pytest
from abc import ABC

from src.retrieval.storage.base import (
    StorageBackend,
    StorageError,
    ConnectionError,
    IntegrityError,
    NotFoundError,
    SerializationError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test storage exception hierarchy."""

    def test_storage_error_is_base_exception(self):
        """Test that StorageError is the base exception."""
        assert issubclass(StorageError, Exception)

        # Can instantiate and raise
        with pytest.raises(StorageError):
            raise StorageError("Test error")

    def test_connection_error_inherits_from_storage_error(self):
        """Test ConnectionError inherits from StorageError."""
        assert issubclass(ConnectionError, StorageError)
        assert issubclass(ConnectionError, Exception)

        with pytest.raises(StorageError):
            raise ConnectionError("Connection failed")

        with pytest.raises(ConnectionError):
            raise ConnectionError("Connection failed")

    def test_integrity_error_inherits_from_storage_error(self):
        """Test IntegrityError inherits from StorageError."""
        assert issubclass(IntegrityError, StorageError)

        with pytest.raises(StorageError):
            raise IntegrityError("Unique constraint violated")

    def test_not_found_error_inherits_from_storage_error(self):
        """Test NotFoundError inherits from StorageError."""
        assert issubclass(NotFoundError, StorageError)

        with pytest.raises(StorageError):
            raise NotFoundError("Resource not found")

    def test_serialization_error_inherits_from_storage_error(self):
        """Test SerializationError inherits from StorageError."""
        assert issubclass(SerializationError, StorageError)

        with pytest.raises(StorageError):
            raise SerializationError("Failed to serialize")

    def test_validation_error_inherits_from_storage_error(self):
        """Test ValidationError inherits from StorageError."""
        assert issubclass(ValidationError, StorageError)

        with pytest.raises(StorageError):
            raise ValidationError("Validation failed")

    def test_catching_base_exception_catches_all(self):
        """Test that catching StorageError catches all specific errors."""
        errors_to_test = [
            ConnectionError("test"),
            IntegrityError("test"),
            NotFoundError("test"),
            SerializationError("test"),
            ValidationError("test"),
        ]

        for error in errors_to_test:
            with pytest.raises(StorageError):
                raise error

    def test_exception_messages(self):
        """Test that exceptions carry custom messages."""
        message = "Custom error message"

        try:
            raise ConnectionError(message)
        except ConnectionError as e:
            assert str(e) == message


class TestAbstractMethodEnforcement:
    """Test that StorageBackend enforces implementation of abstract methods."""

    def test_storage_backend_is_abstract(self):
        """Test that StorageBackend is an abstract base class."""
        assert issubclass(StorageBackend, ABC)

    def test_cannot_instantiate_storage_backend_directly(self):
        """Test that StorageBackend cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            StorageBackend()

    def test_concrete_class_must_implement_connect(self):
        """Test that concrete class must implement connect()."""
        class IncompleteBackend(StorageBackend):
            # Missing connect() implementation
            def disconnect(self): pass
            def is_connected(self): pass
            def initialize_schema(self): pass
            def get_or_create_version(self, model_name, model_version, embedding_dimension): pass
            def get_current_version(self): pass
            def set_current_version(self, version_id): pass
            def store_embedding(self, record): pass
            def store_embeddings_batch(self, records, batch_size=100): pass
            def load_embedding(self, template_id): pass
            def load_embeddings_all(self, version_id=None): pass
            def load_embeddings_by_category(self, category, subcategory=None, version_id=None): pass
            def update_embedding(self, template_id, record): pass
            def delete_embedding(self, template_id): pass
            def exists(self, template_id, version_id=None): pass
            def count(self, version_id=None): pass
            def get_all_template_ids(self, version_id=None): pass
            def get_content_hashes(self, version_id=None): pass
            def validate_integrity(self): pass
            def get_storage_info(self): pass
            def _begin_transaction(self): pass
            def _commit_transaction(self): pass
            def _rollback_transaction(self): pass

        # Should still be abstract because it's missing connect()
        with pytest.raises(TypeError):
            IncompleteBackend()

    def test_concrete_class_with_all_methods_can_be_instantiated(self):
        """Test that implementing all abstract methods allows instantiation."""
        class CompleteBackend(StorageBackend):
            def connect(self): pass
            def disconnect(self): pass
            def is_connected(self): return True
            def initialize_schema(self): pass
            def get_or_create_version(self, model_name, model_version, embedding_dimension): return 1
            def get_current_version(self): return None
            def set_current_version(self, version_id): pass
            def store_embedding(self, record): return 1
            def store_embeddings_batch(self, records, batch_size=100): return []
            def load_embedding(self, template_id): return None
            def load_embeddings_all(self, version_id=None): return []
            def load_embeddings_by_category(self, category, subcategory=None, version_id=None): return []
            def update_embedding(self, template_id, record): return True
            def delete_embedding(self, template_id): return True
            def exists(self, template_id, version_id=None): return False
            def count(self, version_id=None): return 0
            def get_all_template_ids(self, version_id=None): return []
            def get_content_hashes(self, version_id=None): return {}
            def validate_integrity(self): return {"valid": True}
            def get_storage_info(self): return {}
            def _begin_transaction(self): pass
            def _commit_transaction(self): pass
            def _rollback_transaction(self): pass

        # Should be able to instantiate
        backend = CompleteBackend()
        assert isinstance(backend, StorageBackend)
        assert backend.is_connected() is True


class TestContextManagerProtocol:
    """Test context manager protocol (__enter__/__exit__)."""

    def test_context_manager_protocol_exists(self):
        """Test that StorageBackend defines context manager methods."""
        # These should be defined in the base class (not abstract)
        assert hasattr(StorageBackend, '__enter__')
        assert hasattr(StorageBackend, '__exit__')

    def test_context_manager_calls_connect_and_disconnect(self):
        """Test that context manager calls connect() and disconnect()."""
        class TestBackend(StorageBackend):
            def __init__(self):
                self.connected = False
                self.connect_called = False
                self.disconnect_called = False

            def connect(self):
                self.connect_called = True
                self.connected = True

            def disconnect(self):
                self.disconnect_called = True
                self.connected = False

            def is_connected(self):
                return self.connected

            def initialize_schema(self): pass
            def get_or_create_version(self, model_name, model_version, embedding_dimension): return 1
            def get_current_version(self): return None
            def set_current_version(self, version_id): pass
            def store_embedding(self, record): return 1
            def store_embeddings_batch(self, records, batch_size=100): return []
            def load_embedding(self, template_id): return None
            def load_embeddings_all(self, version_id=None): return []
            def load_embeddings_by_category(self, category, subcategory=None, version_id=None): return []
            def update_embedding(self, template_id, record): return True
            def delete_embedding(self, template_id): return True
            def exists(self, template_id, version_id=None): return False
            def count(self, version_id=None): return 0
            def get_all_template_ids(self, version_id=None): return []
            def get_content_hashes(self, version_id=None): return {}
            def validate_integrity(self): return {"valid": True}
            def get_storage_info(self): return {}
            def _begin_transaction(self): pass
            def _commit_transaction(self): pass
            def _rollback_transaction(self): pass

        backend = TestBackend()

        # Use as context manager
        with backend:
            assert backend.connect_called is True

        # After exiting, disconnect should be called
        assert backend.disconnect_called is True

    def test_context_manager_disconnect_called_on_exception(self):
        """Test that disconnect() is called even if exception occurs."""
        class TestBackend(StorageBackend):
            def __init__(self):
                self.disconnect_called = False

            def connect(self): pass

            def disconnect(self):
                self.disconnect_called = True

            def is_connected(self): return True
            def initialize_schema(self): pass
            def get_or_create_version(self, model_name, model_version, embedding_dimension): return 1
            def get_current_version(self): return None
            def set_current_version(self, version_id): pass
            def store_embedding(self, record): return 1
            def store_embeddings_batch(self, records, batch_size=100): return []
            def load_embedding(self, template_id): return None
            def load_embeddings_all(self, version_id=None): return []
            def load_embeddings_by_category(self, category, subcategory=None, version_id=None): return []
            def update_embedding(self, template_id, record): return True
            def delete_embedding(self, template_id): return True
            def exists(self, template_id, version_id=None): return False
            def count(self, version_id=None): return 0
            def get_all_template_ids(self, version_id=None): return []
            def get_content_hashes(self, version_id=None): return {}
            def validate_integrity(self): return {"valid": True}
            def get_storage_info(self): return {}
            def _begin_transaction(self): pass
            def _commit_transaction(self): pass
            def _rollback_transaction(self): pass

        backend = TestBackend()

        # Raise exception inside context
        with pytest.raises(ValueError):
            with backend:
                raise ValueError("Test exception")

        # Disconnect should still be called
        assert backend.disconnect_called is True


class TestTransactionContextManager:
    """Test transaction context manager."""

    def test_transaction_context_manager_exists(self):
        """Test that transaction() method exists."""
        # Should be defined in base class
        assert hasattr(StorageBackend, 'transaction')

    def test_transaction_calls_begin_commit_on_success(self):
        """Test that transaction calls begin and commit."""
        class TestBackend(StorageBackend):
            def __init__(self):
                self.begin_called = False
                self.commit_called = False
                self.rollback_called = False

            def _begin_transaction(self):
                self.begin_called = True

            def _commit_transaction(self):
                self.commit_called = True

            def _rollback_transaction(self):
                self.rollback_called = True

            def connect(self): pass
            def disconnect(self): pass
            def is_connected(self): return True
            def initialize_schema(self): pass
            def get_or_create_version(self, model_name, model_version, embedding_dimension): return 1
            def get_current_version(self): return None
            def set_current_version(self, version_id): pass
            def store_embedding(self, record): return 1
            def store_embeddings_batch(self, records, batch_size=100): return []
            def load_embedding(self, template_id): return None
            def load_embeddings_all(self, version_id=None): return []
            def load_embeddings_by_category(self, category, subcategory=None, version_id=None): return []
            def update_embedding(self, template_id, record): return True
            def delete_embedding(self, template_id): return True
            def exists(self, template_id, version_id=None): return False
            def count(self, version_id=None): return 0
            def get_all_template_ids(self, version_id=None): return []
            def get_content_hashes(self, version_id=None): return {}
            def validate_integrity(self): return {"valid": True}
            def get_storage_info(self): return {}

        backend = TestBackend()

        # Use transaction context manager
        with backend.transaction():
            pass  # Successful transaction

        assert backend.begin_called is True
        assert backend.commit_called is True
        assert backend.rollback_called is False

    def test_transaction_calls_rollback_on_exception(self):
        """Test that transaction calls rollback on exception."""
        class TestBackend(StorageBackend):
            def __init__(self):
                self.rollback_called = False

            def _begin_transaction(self): pass
            def _commit_transaction(self): pass

            def _rollback_transaction(self):
                self.rollback_called = True

            def connect(self): pass
            def disconnect(self): pass
            def is_connected(self): return True
            def initialize_schema(self): pass
            def get_or_create_version(self, model_name, model_version, embedding_dimension): return 1
            def get_current_version(self): return None
            def set_current_version(self, version_id): pass
            def store_embedding(self, record): return 1
            def store_embeddings_batch(self, records, batch_size=100): return []
            def load_embedding(self, template_id): return None
            def load_embeddings_all(self, version_id=None): return []
            def load_embeddings_by_category(self, category, subcategory=None, version_id=None): return []
            def update_embedding(self, template_id, record): return True
            def delete_embedding(self, template_id): return True
            def exists(self, template_id, version_id=None): return False
            def count(self, version_id=None): return 0
            def get_all_template_ids(self, version_id=None): return []
            def get_content_hashes(self, version_id=None): return {}
            def validate_integrity(self): return {"valid": True}
            def get_storage_info(self): return {}

        backend = TestBackend()

        # Raise exception inside transaction
        with pytest.raises(ValueError):
            with backend.transaction():
                raise ValueError("Test error")

        # Rollback should be called
        assert backend.rollback_called is True
