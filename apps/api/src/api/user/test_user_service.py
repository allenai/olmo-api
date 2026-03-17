from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from unittest.mock import AsyncMock, Mock

import pytest
from psycopg.errors import UniqueViolation
from rfc9457 import ConflictProblem
from sqlalchemy.exc import IntegrityError

from api.user.user_service import UpsertUserRequest, UserService
from core.auth.token import Token
from db.models.user import User

ANONYMOUS_CLIENT = "anon-user-client-id"


async def test_user_upsert_retries_on_conflict():
    mock_session = AsyncMock()

    first_scalar_result = Mock()
    first_scalar_result.one_or_none = Mock(return_value=None)

    second_scalar_result = Mock()
    existing_user = User(
        id="existing-user=id",
        client=ANONYMOUS_CLIENT,
        terms_accepted_date=datetime.now(UTC) - timedelta(days=1),  # past
        acceptance_revoked_date=None,
        data_collection_acceptance_revoked_date=None,
        data_collection_accepted_date=None,
        media_collection_acceptance_revoked_date=None,
        media_collection_accepted_date=None,
    )
    second_scalar_result.one = Mock(return_value=existing_user)

    mock_session.scalars = AsyncMock(side_effect=[first_scalar_result, second_scalar_result])

    unique_violation = IntegrityError(statement=None, params=None, orig=UniqueViolation())
    mock_session.flush = AsyncMock(side_effect=[unique_violation, None])

    service = UserService(session=mock_session, hubspot_service=AsyncMock())

    request = UpsertUserRequest(terms_accepted_date=datetime.now(UTC))

    result = await service.upsert_user(
        request, Token(client=ANONYMOUS_CLIENT, is_anonymous_user=True, token="client-token")
    )

    assert mock_session.rollback.called
    # check that updated accept_date is from second request
    assert result.terms_accepted_date == request.terms_accepted_date
    assert existing_user.terms_accepted_date == request.terms_accepted_date


async def test_user_upsert_fails_on_second_conflict():
    mock_session = AsyncMock()

    first_scalar_result = Mock()
    first_scalar_result.one_or_none = Mock(return_value=None)

    second_scalar_result = Mock()
    existing_user = User(
        id="existing-user=id",
        client=ANONYMOUS_CLIENT,
        terms_accepted_date=datetime.now(UTC) - timedelta(days=1),  # past
        acceptance_revoked_date=None,
        data_collection_acceptance_revoked_date=None,
        data_collection_accepted_date=None,
        media_collection_acceptance_revoked_date=None,
        media_collection_accepted_date=None,
    )
    second_scalar_result.one = Mock(return_value=existing_user)

    mock_session.scalars = AsyncMock(side_effect=[first_scalar_result, second_scalar_result])

    unique_violation = IntegrityError(statement=None, params=None, orig=UniqueViolation())
    mock_session.flush = AsyncMock(side_effect=[unique_violation, unique_violation])

    service = UserService(session=mock_session, hubspot_service=AsyncMock())

    request = UpsertUserRequest(terms_accepted_date=datetime.now(UTC))

    with pytest.raises(ConflictProblem) as e:
        await service.upsert_user(request, Token(client=ANONYMOUS_CLIENT, is_anonymous_user=True, token="client-token"))

    assert e.value.status_code == HTTPStatus.CONFLICT
