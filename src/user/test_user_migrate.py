from datetime import datetime, timezone
from unittest.mock import Mock

from src.dao.engine_models.message import Message
from src.dao.engine_models.model_config import ModelHost
from src.dao.message.message_models import Role
from src.obj import NewID
from src.user.user_migrate import migrate_user_from_anonymous_user


class TestMigrateUserFromAnonymousUser:
    """Test cases for migrate_user_from_anonymous_user function."""

    def test_migrate_when_both_users_exist(self, dbc, sql_alchemy):
        """Test migration when both anonymous and new users exist."""
        # Setup test data
        anonymous_user_id = "anonymous_user_123"
        new_user_id = "new_user_456"

        # Create anonymous user
        anonymous_user = dbc.user.create(
            client=anonymous_user_id,
            terms_accepted_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            data_collection_accepted_date=datetime(2023, 1, 15, tzinfo=timezone.utc),
        )

        # Create new user with different dates
        new_user = dbc.user.create(
            client=new_user_id,
            terms_accepted_date=datetime(2023, 2, 1, tzinfo=timezone.utc),
            data_collection_accepted_date=datetime(2023, 2, 15, tzinfo=timezone.utc),
        )

        # Create messages for anonymous user
        message1_id = NewID("msg")
        message1 = Message(
            id=message1_id,
            content="Test message 1",
            creator=anonymous_user_id,
            role=Role.User.value,
            root=message1_id,
            opts={},
            final=True,
            private=False,
            model_id="test-model",
            model_host=ModelHost.TestBackend.value,
            parent=None,
            expiration_time=None,
            file_urls=["https://storage.googleapis.com/bucket/anonymous/file1.txt"],
        )

        message2_id = NewID("msg")
        message2 = Message(
            id=message2_id,
            content="Test message 2",
            creator=anonymous_user_id,
            role=Role.Assistant.value,
            root=message1_id,  # Same root as message1
            opts={},
            final=True,
            private=False,
            model_id="test-model",
            model_host=ModelHost.TestBackend.value,
            parent=message1_id,
            expiration_time=None,
        )

        sql_alchemy.add(message1)
        sql_alchemy.add(message2)
        sql_alchemy.commit()

        # Mock GoogleCloudStorage
        mock_storage = Mock()
        mock_storage.migrate_anonymous_file.return_value = None

        # Execute migration
        result = migrate_user_from_anonymous_user(
            dbc=dbc, storage_client=mock_storage, session=sql_alchemy, anonymous_user_id=anonymous_user_id, new_user_id=new_user_id
        )

        # Verify results
        assert result.updated_user is not None
        assert result.updated_user.client == new_user_id
        assert result.messages_updated_count == 2

        # Verify user data was merged (should use most recent dates)
        assert result.updated_user.terms_accepted_date == datetime(2023, 2, 1, tzinfo=timezone.utc)
        assert result.updated_user.data_collection_accepted_date == datetime(2023, 2, 15, tzinfo=timezone.utc)

        # Verify messages were migrated
        migrated_messages = sql_alchemy.query(Message).filter(Message.creator == new_user_id).all()
        assert len(migrated_messages) == 2

        # Verify storage migration was called for files
        assert mock_storage.migrate_anonymous_file.call_count == 1
        mock_storage.migrate_anonymous_file.assert_called_with(f"{message1_id}/file1.txt")

        # Verify anonymous user messages no longer exist
        anonymous_messages = sql_alchemy.query(Message).filter(Message.creator == anonymous_user_id).all()
        assert len(anonymous_messages) == 0

    def test_migrate_when_only_anonymous_user_exists(self, dbc, sql_alchemy):
        """Test migration when only anonymous user exists (new user doesn't exist)."""
        # Setup test data
        anonymous_user_id = "anonymous_user_789"
        new_user_id = "new_user_101"

        # Create only anonymous user
        anonymous_user = dbc.user.create(
            client=anonymous_user_id,
            terms_accepted_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
            data_collection_accepted_date=datetime(2023, 1, 15, tzinfo=timezone.utc),
        )

        # Create messages for anonymous user
        message_id = NewID("msg")
        message = Message(
            id=message_id,
            content="Test message for anonymous user",
            creator=anonymous_user_id,
            role=Role.User.value,
            root=message_id,
            opts={},
            final=True,
            private=False,
            model_id="test-model",
            model_host=ModelHost.TestBackend.value,
            parent=None,
            expiration_time=None,
        )

        sql_alchemy.add(message)
        sql_alchemy.commit()

        # Mock GoogleCloudStorage
        mock_storage = Mock()
        mock_storage.migrate_anonymous_file.return_value = None

        # Execute migration
        result = migrate_user_from_anonymous_user(
            dbc=dbc, storage_client=mock_storage, session=sql_alchemy, anonymous_user_id=anonymous_user_id, new_user_id=new_user_id
        )

        # Verify results
        assert result.updated_user is not None
        assert result.updated_user.client == new_user_id
        assert result.messages_updated_count == 1

        # Verify user data was copied from anonymous user
        assert result.updated_user.terms_accepted_date == datetime(2023, 1, 1, tzinfo=timezone.utc)
        assert result.updated_user.data_collection_accepted_date == datetime(2023, 1, 15, tzinfo=timezone.utc)

        # Verify messages were migrated
        migrated_messages = sql_alchemy.query(Message).filter(Message.creator == new_user_id).all()
        assert len(migrated_messages) == 1
        assert migrated_messages[0].content == "Test message for anonymous user"

    def test_migrate_when_only_new_user_exists(self, dbc, sql_alchemy):
        """Test migration when only new user exists (anonymous user doesn't exist)."""
        # Setup test data
        anonymous_user_id = "anonymous_user_999"
        new_user_id = "new_user_202"

        # Create only new user
        new_user = dbc.user.create(
            client=new_user_id,
            terms_accepted_date=datetime(2023, 3, 1, tzinfo=timezone.utc),
            data_collection_accepted_date=datetime(2023, 3, 15, tzinfo=timezone.utc),
        )

        # Mock GoogleCloudStorage
        mock_storage = Mock()
        mock_storage.migrate_anonymous_file.return_value = None

        # Execute migration
        result = migrate_user_from_anonymous_user(
            dbc=dbc, storage_client=mock_storage, session=sql_alchemy, anonymous_user_id=anonymous_user_id, new_user_id=new_user_id
        )

        # Verify results
        assert result.updated_user is not None
        assert result.updated_user.client == new_user_id
        assert result.messages_updated_count == 0  # No messages to migrate

        # Verify user data remains unchanged
        assert result.updated_user.terms_accepted_date == datetime(2023, 3, 1, tzinfo=timezone.utc)
        assert result.updated_user.data_collection_accepted_date == datetime(2023, 3, 15, tzinfo=timezone.utc)

        # Verify no storage migration was called
        mock_storage.migrate_anonymous_file.assert_not_called()

    def test_migrate_when_neither_user_exists(self, dbc, sql_alchemy):
        """Test migration when neither user exists."""
        # Setup test data
        anonymous_user_id = "anonymous_user_404"
        new_user_id = "new_user_505"

        # Mock GoogleCloudStorage
        mock_storage = Mock()
        mock_storage.migrate_anonymous_file.return_value = None

        # Execute migration
        result = migrate_user_from_anonymous_user(
            dbc=dbc, storage_client=mock_storage, session=sql_alchemy, anonymous_user_id=anonymous_user_id, new_user_id=new_user_id
        )

        # Verify results
        assert result.updated_user is None
        assert result.messages_updated_count == 0

        # Verify no storage migration was called
        mock_storage.migrate_anonymous_file.assert_not_called()

    def test_migrate_with_multiple_messages_and_files(self, dbc, sql_alchemy):
        """Test migration with multiple messages and file URLs."""
        # Setup test data
        anonymous_user_id = "anonymous_user_multi"
        new_user_id = "new_user_multi"

        # Create users
        anonymous_user = dbc.user.create(
            client=anonymous_user_id,
            terms_accepted_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )

        new_user = dbc.user.create(
            client=new_user_id,
            terms_accepted_date=datetime(2023, 2, 1, tzinfo=timezone.utc),
        )

        # Create multiple messages with different file URLs
        messages = []
        for i in range(3):
            message_id = NewID("msg")
            message = Message(
                id=message_id,
                content=f"Test message {i + 1}",
                creator=anonymous_user_id,
                role=Role.User.value if i % 2 == 0 else Role.Assistant.value,
                root=message_id,
                opts={},
                final=True,
                private=False,
                model_id="test-model",
                model_host=ModelHost.TestBackend.value,
                parent=None,
                expiration_time=None,
                file_urls=[f"https://storage.googleapis.com/bucket/anonymous/file{i + 1}.txt"] if i < 2 else None,
            )
            messages.append(message)
            sql_alchemy.add(message)

        sql_alchemy.commit()

        # Mock GoogleCloudStorage
        mock_storage = Mock()
        mock_storage.migrate_anonymous_file.return_value = None

        # Execute migration
        result = migrate_user_from_anonymous_user(
            dbc=dbc, storage_client=mock_storage, session=sql_alchemy, anonymous_user_id=anonymous_user_id, new_user_id=new_user_id
        )

        # Verify results
        assert result.updated_user is not None
        assert result.messages_updated_count == 3

        # Verify all messages were migrated
        migrated_messages = sql_alchemy.query(Message).filter(Message.creator == new_user_id).all()
        assert len(migrated_messages) == 3

        # Verify storage migration was called for each file
        assert mock_storage.migrate_anonymous_file.call_count == 2  # Only 2 messages have files
        expected_calls = [(f"{messages[0].id}/file1.txt",), (f"{messages[1].id}/file2.txt",)]
        actual_calls = [call[0] for call in mock_storage.migrate_anonymous_file.call_args_list]
        assert actual_calls == expected_calls
