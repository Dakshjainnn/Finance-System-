from app.models.user import UserRole
from tests.conftest import auth_header, make_user


def test_get_current_user(client, db):
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.get("/users/me", headers=auth_header("viewer1"))
    assert resp.status_code == 200
    assert resp.json()["username"] == "viewer1"
    assert resp.json()["role"] == "viewer"


def test_admin_list_users(client, db):
    make_user(db, "admin1", UserRole.admin)
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.get("/users/", headers=auth_header("admin1"))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_viewer_cannot_list_users(client, db):
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.get("/users/", headers=auth_header("viewer1"))
    assert resp.status_code == 403


def test_analyst_cannot_list_users(client, db):
    make_user(db, "analyst1", UserRole.analyst)
    resp = client.get("/users/", headers=auth_header("analyst1"))
    assert resp.status_code == 403


def test_admin_update_role(client, db):
    make_user(db, "admin1", UserRole.admin)
    target = make_user(db, "viewer1", UserRole.viewer)
    resp = client.patch(
        f"/users/{target.id}/role",
        json={"role": "analyst"},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "analyst"


def test_admin_cannot_change_own_role(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    resp = client.patch(
        f"/users/{admin.id}/role",
        json={"role": "viewer"},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 400


def test_admin_delete_user(client, db):
    make_user(db, "admin1", UserRole.admin)
    target = make_user(db, "victim", UserRole.viewer)
    resp = client.delete(
        f"/users/{target.id}",
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 204


def test_admin_cannot_delete_self(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    resp = client.delete(
        f"/users/{admin.id}",
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 400


def test_update_nonexistent_user_role(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.patch(
        "/users/99999/role",
        json={"role": "analyst"},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 404


def test_delete_nonexistent_user(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.delete(
        "/users/99999",
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 404
