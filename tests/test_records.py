from app.models.user import UserRole
from tests.conftest import auth_header, make_user


# --- Record Creation (Admin only) ---


def test_create_record(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.post(
        "/records/",
        json={
            "amount": 1500.0,
            "type": "income",
            "category": "Salary",
            "date": "2026-03-15",
            "notes": "March salary",
        },
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 1500.0
    assert data["type"] == "income"
    assert data["category"] == "Salary"
    assert data["notes"] == "March salary"


def test_create_record_invalid_amount(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.post(
        "/records/",
        json={"amount": -100, "type": "income", "category": "Bad"},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 422


def test_create_record_zero_amount(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.post(
        "/records/",
        json={"amount": 0, "type": "income", "category": "Zero"},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 422


def test_create_record_missing_fields(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.post(
        "/records/",
        json={"amount": 100},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 422


def test_create_record_unauthenticated(client):
    resp = client.post("/records/", json={
        "amount": 100, "type": "income", "category": "Test",
    })
    assert resp.status_code == 401


def test_viewer_cannot_create_record(client, db):
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.post(
        "/records/",
        json={"amount": 100, "type": "income", "category": "Test"},
        headers=auth_header("viewer1"),
    )
    assert resp.status_code == 403


def test_analyst_cannot_create_record(client, db):
    make_user(db, "analyst1", UserRole.analyst)
    resp = client.post(
        "/records/",
        json={"amount": 100, "type": "income", "category": "Test"},
        headers=auth_header("analyst1"),
    )
    assert resp.status_code == 403


# --- Record Listing & Pagination (Viewer can list, Analyst can filter) ---


def test_list_records_with_pagination(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    for i in range(5):
        client.post(
            "/records/",
            json={"amount": 100 + i, "type": "expense", "category": "Food"},
            headers=auth_header("admin1"),
        )
    resp = client.get(
        "/records/?page=1&per_page=2",
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3


def test_viewer_can_list_records_without_filters(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    viewer = make_user(db, "viewer1", UserRole.viewer)
    # Admin creates a record for viewer to see (we need the viewer's record)
    # Actually, records are user-scoped. Let's create via admin for admin's records.
    client.post(
        "/records/",
        json={"amount": 500, "type": "income", "category": "Salary"},
        headers=auth_header("admin1"),
    )
    # Viewer lists their own records (empty, but the endpoint should work)
    resp = client.get("/records/", headers=auth_header("viewer1"))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_viewer_cannot_use_filters(client, db):
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.get(
        "/records/?type=income",
        headers=auth_header("viewer1"),
    )
    assert resp.status_code == 403
    assert "analyst" in resp.json()["detail"].lower()


def test_analyst_can_use_filters(client, db):
    make_user(db, "admin1", UserRole.admin)
    make_user(db, "analyst1", UserRole.analyst)
    # Create records as admin, then filter as analyst (analyst sees own records only)
    resp = client.get(
        "/records/?type=income",
        headers=auth_header("analyst1"),
    )
    assert resp.status_code == 200


def test_list_records_filter_by_type(client, db):
    make_user(db, "admin1", UserRole.admin)
    client.post(
        "/records/",
        json={"amount": 500, "type": "income", "category": "Salary"},
        headers=auth_header("admin1"),
    )
    client.post(
        "/records/",
        json={"amount": 50, "type": "expense", "category": "Food"},
        headers=auth_header("admin1"),
    )
    resp = client.get(
        "/records/?type=income",
        headers=auth_header("admin1"),
    )
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["type"] == "income"


def test_list_records_filter_by_date_range(client, db):
    make_user(db, "admin1", UserRole.admin)
    headers = auth_header("admin1")
    client.post("/records/", json={"amount": 100, "type": "income", "category": "A", "date": "2026-01-15"}, headers=headers)
    client.post("/records/", json={"amount": 200, "type": "income", "category": "B", "date": "2026-03-15"}, headers=headers)
    client.post("/records/", json={"amount": 300, "type": "income", "category": "C", "date": "2026-06-15"}, headers=headers)

    resp = client.get(
        "/records/?start_date=2026-02-01&end_date=2026-04-01",
        headers=headers,
    )
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["amount"] == 200


def test_list_records_filter_by_category(client, db):
    make_user(db, "admin1", UserRole.admin)
    headers = auth_header("admin1")
    client.post("/records/", json={"amount": 100, "type": "expense", "category": "Food"}, headers=headers)
    client.post("/records/", json={"amount": 200, "type": "expense", "category": "Rent"}, headers=headers)

    resp = client.get("/records/?category=Food", headers=headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "Food"


# --- Get Single Record ---


def test_get_record_by_id(client, db):
    make_user(db, "admin1", UserRole.admin)
    headers = auth_header("admin1")
    create_resp = client.post(
        "/records/",
        json={"amount": 250, "type": "expense", "category": "Transport"},
        headers=headers,
    )
    record_id = create_resp.json()["id"]

    resp = client.get(f"/records/{record_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["amount"] == 250


def test_get_nonexistent_record(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.get("/records/99999", headers=auth_header("admin1"))
    assert resp.status_code == 404


def test_viewer_cannot_access_other_users_record(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    viewer = make_user(db, "viewer1", UserRole.viewer)
    create_resp = client.post(
        "/records/",
        json={"amount": 100, "type": "income", "category": "Test"},
        headers=auth_header("admin1"),
    )
    record_id = create_resp.json()["id"]

    resp = client.get(f"/records/{record_id}", headers=auth_header("viewer1"))
    assert resp.status_code == 403


# --- Update & Delete (Admin only) ---


def test_viewer_cannot_delete(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    make_user(db, "viewer1", UserRole.viewer)
    create_resp = client.post(
        "/records/",
        json={"amount": 100, "type": "expense", "category": "Test"},
        headers=auth_header("admin1"),
    )
    record_id = create_resp.json()["id"]
    resp = client.delete(
        f"/records/{record_id}",
        headers=auth_header("viewer1"),
    )
    assert resp.status_code == 403


def test_viewer_cannot_update(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    make_user(db, "viewer1", UserRole.viewer)
    create_resp = client.post(
        "/records/",
        json={"amount": 100, "type": "expense", "category": "Test"},
        headers=auth_header("admin1"),
    )
    record_id = create_resp.json()["id"]
    resp = client.put(
        f"/records/{record_id}",
        json={"amount": 200},
        headers=auth_header("viewer1"),
    )
    assert resp.status_code == 403


def test_analyst_cannot_delete(client, db):
    admin = make_user(db, "admin1", UserRole.admin)
    make_user(db, "analyst1", UserRole.analyst)
    create_resp = client.post(
        "/records/",
        json={"amount": 100, "type": "expense", "category": "Test"},
        headers=auth_header("admin1"),
    )
    record_id = create_resp.json()["id"]
    resp = client.delete(
        f"/records/{record_id}",
        headers=auth_header("analyst1"),
    )
    assert resp.status_code == 403


def test_admin_can_delete(client, db):
    make_user(db, "admin1", UserRole.admin)
    create_resp = client.post(
        "/records/",
        json={"amount": 100, "type": "expense", "category": "Test"},
        headers=auth_header("admin1"),
    )
    record_id = create_resp.json()["id"]
    resp = client.delete(
        f"/records/{record_id}",
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 204


def test_admin_can_update(client, db):
    make_user(db, "admin1", UserRole.admin)
    create_resp = client.post(
        "/records/",
        json={"amount": 100, "type": "expense", "category": "Food"},
        headers=auth_header("admin1"),
    )
    record_id = create_resp.json()["id"]
    resp = client.put(
        f"/records/{record_id}",
        json={"amount": 200, "category": "Dining"},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 200
    assert resp.json()["category"] == "Dining"


def test_update_nonexistent_record(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.put(
        "/records/99999",
        json={"amount": 200},
        headers=auth_header("admin1"),
    )
    assert resp.status_code == 404


# --- Summary & Analytics ---


def test_summary(client, db):
    make_user(db, "admin1", UserRole.admin)
    headers = auth_header("admin1")
    client.post("/records/", json={"amount": 3000, "type": "income", "category": "Salary"}, headers=headers)
    client.post("/records/", json={"amount": 500, "type": "expense", "category": "Rent"}, headers=headers)
    client.post("/records/", json={"amount": 100, "type": "expense", "category": "Food"}, headers=headers)

    resp = client.get("/records/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_income"] == 3000
    assert data["total_expenses"] == 600
    assert data["balance"] == 2400
    assert len(data["by_category"]) == 3


def test_viewer_can_access_summary(client, db):
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.get("/records/summary", headers=auth_header("viewer1"))
    assert resp.status_code == 200


def test_monthly_totals(client, db):
    make_user(db, "analyst1", UserRole.analyst)
    # We need an admin to create records, or we use analyst... but analyst can't create.
    # Let's use admin to create, then analyst to view their own (empty).
    # Better: use admin who inherits analyst access.
    make_user(db, "admin1", UserRole.admin)
    headers = auth_header("admin1")
    client.post("/records/", json={"amount": 1000, "type": "income", "category": "Salary", "date": "2026-01-15"}, headers=headers)
    client.post("/records/", json={"amount": 200, "type": "expense", "category": "Food", "date": "2026-01-20"}, headers=headers)
    client.post("/records/", json={"amount": 1500, "type": "income", "category": "Salary", "date": "2026-02-15"}, headers=headers)

    resp = client.get("/records/monthly", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    jan = next(m for m in data if m["month"] == "2026-01")
    assert jan["income"] == 1000
    assert jan["expense"] == 200


def test_viewer_cannot_access_monthly(client, db):
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.get("/records/monthly", headers=auth_header("viewer1"))
    assert resp.status_code == 403


def test_recent_activity(client, db):
    make_user(db, "admin1", UserRole.admin)
    headers = auth_header("admin1")
    for i in range(3):
        client.post("/records/", json={"amount": 100 + i, "type": "income", "category": "Test"}, headers=headers)

    resp = client.get("/records/recent?limit=2", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# --- Export ---


def test_export_json(client, db):
    make_user(db, "analyst1", UserRole.analyst)
    # Analyst can't create records, so use admin
    make_user(db, "admin1", UserRole.admin)
    headers_admin = auth_header("admin1")
    # Admin creates, admin exports (admin inherits analyst)
    client.post("/records/", json={"amount": 100, "type": "income", "category": "Test"}, headers=headers_admin)

    resp = client.get("/records/export?format=json", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_export_csv(client, db):
    make_user(db, "admin1", UserRole.admin)
    headers = auth_header("admin1")
    client.post("/records/", json={"amount": 100, "type": "income", "category": "Test"}, headers=headers)

    resp = client.get("/records/export?format=csv", headers=headers)
    assert resp.status_code == 200
    assert "id,amount,type,category,date,notes" in resp.text


def test_viewer_cannot_export(client, db):
    make_user(db, "viewer1", UserRole.viewer)
    resp = client.get("/records/export?format=json", headers=auth_header("viewer1"))
    assert resp.status_code == 403


def test_summary_empty_records(client, db):
    make_user(db, "admin1", UserRole.admin)
    resp = client.get("/records/summary", headers=auth_header("admin1"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_income"] == 0
    assert data["total_expenses"] == 0
    assert data["balance"] == 0
