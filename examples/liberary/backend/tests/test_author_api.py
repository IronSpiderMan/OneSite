# backend/tests/test_author_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel
from app.main import app
from app.core import db, deps
from app.models.author import Author


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    async with TestingSessionLocal() as session:
        yield session


async def override_get_current_user():
    from app.models.user import User
    async with TestingSessionLocal() as session:
        # Create test user if not exists
        user = await session.get(User, 1)
        if not user:
            user = User(id=1, username="testuser", email="test@test.com", hashed_password="", is_superuser=True)
            session.add(user)
            await session.commit()
        return user


app.dependency_overrides[deps.get_session] = override_get_session
app.dependency_overrides[deps.get_current_user] = override_get_current_user


@pytest.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac



class TestAuthorAPI:
    @pytest.mark.asyncio
    async def test_list_authors(self, client):
        """Test listing Author records"""
        response = await client.get("/authors/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data

    @pytest.mark.asyncio
    async def test_create_author(self, client):
        """Test creating a Author record"""
        payload = {




            "name": "",


        }
        response = await client.post("/authors/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_author(self, client):
        """Test getting a single Author record"""
        # First create
        payload = {




            "name": "",


        }
        create_response = await client.post("/authors/", json=payload)
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        # Then get
        response = await client.get("/authors/{created_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_id

    @pytest.mark.asyncio
    async def test_update_author(self, client):
        """Test updating a Author record"""
        # First create
        payload = {




            "name": "",


        }
        create_response = await client.post("/authors/", json=payload)
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        # Then update
        update_payload = {




            "name": "updated",


        }
        response = await client.put("/authors/{created_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_id

    @pytest.mark.asyncio
    async def test_delete_author(self, client):
        """Test deleting a Author record"""
        # First create
        payload = {




            "name": "",


        }
        create_response = await client.post("/authors/", json=payload)
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        # Then delete
        response = await client.delete("/authors/{created_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = await client.get("/authors/{created_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_author_not_found(self, client):
        """Test getting a non-existent Author record"""
        response = await client.get("/authors/999999")
        assert response.status_code == 404

