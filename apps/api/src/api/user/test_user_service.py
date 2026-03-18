from http import HTTPStatus
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi_problem.error import ConflictProblem
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError

from api.user.user_service import UpsertUserRequest, UserService
from core.auth.token import Token


async def test_user_upsert_raises_conflict_on_duplicate():
    mock_session = AsyncMock()
    scalars = Mock()

    scalars.one_or_none = Mock(return_value=None)
    mock_session.scalars = AsyncMock(return_value=scalars)

    unique_violation = IntegrityError(statement=None, params=None, orig=UniqueViolation())
    mock_session.flush = AsyncMock(side_effect=unique_violation)

    service = UserService(session=mock_session, hubspot_service=AsyncMock())

    with pytest.raises(ConflictProblem) as e:
        await service.upsert_user(
            UpsertUserRequest(), Token(client="anon-user-client-id", is_anonymous_user=True, token="client-token")
        )

    assert e.value.status_code == HTTPStatus.CONFLICT
