import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, status
from app.users.routes import create_user, get_user, list_users
from app.users.schemas import UserCreate
from app.users.models import User


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_user_success(mock_db_session):
    user_in = UserCreate(name="Unit Test", email="unit@test.com")

    # Mock para 'email not found'
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    # Executa
    new_user = await create_user(user_in, db=mock_db_session)

    assert new_user.email == "unit@test.com"
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_create_user_duplicate_email(mock_db_session):
    user_in = UserCreate(name="Dup", email="dup@test.com")

    # Mock para 'email found'
    mock_user_db = User(id=1, name="Existing", email="dup@test.com")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user_db
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await create_user(user_in, db=mock_db_session)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email já registrado" in exc.value.detail
    assert not mock_db_session.add.called


@pytest.mark.asyncio
async def test_get_user_found(mock_db_session):
    mock_user = User(id=99, name="Found", email="found@test.com")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db_session.execute.return_value = mock_result

    user = await get_user(user_id=99, db=mock_db_session)
    assert user.id == 99
    assert user.name == "Found"


@pytest.mark.asyncio
async def test_get_user_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc:
        await get_user(user_id=999, db=mock_db_session)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_list_users(mock_db_session):
    users_db = [User(id=1, name="A"), User(id=2, name="B")]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = users_db
    mock_db_session.execute.return_value = mock_result

    result = await list_users(skip=0, limit=10, db=mock_db_session)
    assert len(result) == 2
    assert result[0].name == "A"
