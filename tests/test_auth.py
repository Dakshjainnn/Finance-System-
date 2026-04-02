from app.models.user import UserRole
from tests.conftest import make_user


def test_register_success(client):
    resp = client.post("/auth/register", json={
        "username": "newuser",
        "password": "secret123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["role"] == "viewer"


def test_register_always_assigns_viewer(client):
    """Registration must always create viewer accounts, ignoring any role field."""
    resp = client.post("/auth/register", json={
        "username": "sneaky",
        "password": "secret123",
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "viewer"


def test_register_duplicate_username(client, db):
    make_user(db, "existing", UserRole.viewer)
    resp = client.post("/auth/register", json={
        "username": "existing",
        "password": "secret123",
    })
    assert resp.status_code == 400
    assert "already taken" in resp.json()["detail"]


def test_register_short_password(client):
    resp = client.post("/auth/register", json={
        "username": "user1",
        "password": "abc",
    })
    assert resp.status_code == 422


def test_register_short_username(client):
    resp = client.post("/auth/register", json={
        "username": "ab",
        "password": "secret123",
    })
    assert resp.status_code == 422


def test_login_success(client, db):
    make_user(db, "loginuser", UserRole.viewer, password="mypassword")
    resp = client.post("/auth/login", data={
        "username": "loginuser",
        "password": "mypassword",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client, db):
    make_user(db, "loginuser", UserRole.viewer, password="mypassword")
    resp = client.post("/auth/login", data={
        "username": "loginuser",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/auth/login", data={
        "username": "ghost",
        "password": "whatever",
    })
    assert resp.status_code == 401


def test_access_protected_route_without_token(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_access_with_invalid_token(client):
    resp = client.get("/users/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
