# Finance Tracker API

A Python-powered personal finance tracking system built with FastAPI, SQLAlchemy, and SQLite. Supports income/expense management, financial analytics, role-based access control, and data export.

## Tech Stack

- **Framework:** FastAPI
- **Database:** SQLite via SQLAlchemy ORM
- **Authentication:** JWT (python-jose + bcrypt)
- **Validation:** Pydantic v2
- **Testing:** pytest + httpx

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python run.py
```

The API starts at **http://localhost:8000**

- Interactive docs (Swagger UI): **http://localhost:8000/docs**
- Alternative docs (ReDoc): **http://localhost:8000/redoc**

A default admin user is created on first run:
- Username: `admin`
- Password: `admin123`

## Configuration

Settings can be overridden via environment variables or a `.env` file. See `.env.example` for available options:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./finance.db` | Database connection string |
| `SECRET_KEY` | *(built-in default)* | JWT signing key (override in production) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiry duration |

## Project Structure

```
app/
  main.py           # FastAPI app entry point, startup seed
  config.py         # Settings (DB URL, JWT secret, token expiry)
  database.py       # SQLAlchemy engine and session
  dependencies.py   # Auth dependencies and role-based access control
  models/           # SQLAlchemy ORM models (User, FinancialRecord)
  schemas/          # Pydantic request/response schemas
  services/         # Business logic layer (auth, records, users)
  routers/          # API route handlers (auth, records, users)
tests/              # Unit tests (auth, records, users)
```

## Roles and Permissions

The system uses a hierarchical role model: **Viewer < Analyst < Admin**. Each higher role inherits all permissions of the roles below it.

| Action | Viewer | Analyst | Admin |
|--------|--------|---------|-------|
| View own records (list, get by ID) | Yes | Yes | Yes |
| View financial summary | Yes | Yes | Yes |
| View recent activity | Yes | Yes | Yes |
| Filter records (type, category, date) | - | Yes | Yes |
| View monthly breakdown | - | Yes | Yes |
| Export records (CSV/JSON) | - | Yes | Yes |
| Create records | - | - | Yes |
| Update records | - | - | Yes |
| Delete records | - | - | Yes |
| Manage users (list, update role, delete) | - | - | Yes |

New users always register as **Viewer**. Only an Admin can promote users to higher roles.

## API Endpoints

### Authentication
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/register` | Create a new account (always viewer role) | None |
| POST | `/auth/login` | Get JWT token | None |

### Financial Records
| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|----------|
| POST | `/records/` | Create a record | Admin |
| GET | `/records/` | List records (pagination only for viewer; filters for analyst+) | Viewer |
| GET | `/records/{id}` | Get a single record (own records; admin can view any) | Viewer |
| PUT | `/records/{id}` | Update a record | Admin |
| DELETE | `/records/{id}` | Delete a record | Admin |
| GET | `/records/summary` | Income/expense/balance summary with category breakdown | Viewer |
| GET | `/records/monthly` | Monthly income/expense totals | Analyst |
| GET | `/records/recent` | Recent activity | Viewer |
| GET | `/records/export?format=csv` | Export records as CSV or JSON | Analyst |

### User Management
| Method | Endpoint | Description | Min Role |
|--------|----------|-------------|----------|
| GET | `/users/me` | Get current user profile | Any authenticated |
| GET | `/users/` | List all users | Admin |
| PATCH | `/users/{id}/role` | Change a user's role | Admin |
| DELETE | `/users/{id}` | Delete a user | Admin |

### Filtering & Pagination

`GET /records/` supports these query parameters:

- `type` - Filter by `income` or `expense` *(analyst+ only)*
- `category` - Filter by category name *(analyst+ only)*
- `start_date` - Filter from date (YYYY-MM-DD) *(analyst+ only)*
- `end_date` - Filter to date (YYYY-MM-DD) *(analyst+ only)*
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 20, max: 100)

## Example Usage

### Register and Login

```bash
# Register (always creates a viewer account)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "mypassword"}'

# Login (returns JWT token)
curl -X POST http://localhost:8000/auth/login \
  -d "username=john&password=mypassword"
```

### Create and Query Records (Admin)

```bash
TOKEN="your-jwt-token"

# Create a record (admin only)
curl -X POST http://localhost:8000/records/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000, "type": "income", "category": "Salary", "date": "2026-03-01", "notes": "March salary"}'

# List records with filters (analyst+)
curl "http://localhost:8000/records/?type=expense&category=Food&page=1&per_page=10" \
  -H "Authorization: Bearer $TOKEN"

# Get financial summary (viewer+)
curl http://localhost:8000/records/summary \
  -H "Authorization: Bearer $TOKEN"

# Export as CSV (analyst+)
curl http://localhost:8000/records/export?format=csv \
  -H "Authorization: Bearer $TOKEN" -o records.csv
```

## Running Tests

```bash
pytest tests/ -v
```

52 tests covering authentication, CRUD operations, role enforcement, analytics, pagination, filtering, and export.

## Design Decisions

- **FastAPI** was chosen for auto-generated Swagger docs, built-in Pydantic validation, and clean dependency injection for RBAC.
- **SQLite** requires zero setup while demonstrating proper ORM usage. The schema is designed to work with any SQLAlchemy-supported database by changing `DATABASE_URL`.
- **Service layer** separates business logic from route handlers, keeping routers thin and logic independently testable.
- **Hierarchical role system** (`RoleRequired` dependency class) provides one-liner role enforcement per endpoint. Viewer < Analyst < Admin, with each role inheriting all permissions below it.
- **Filter enforcement** is done at the route level: viewers can list records but filter parameters require analyst role, demonstrating fine-grained RBAC.
- **SQL aggregations** (`func.sum`, `group_by`) are used for analytics instead of loading all records into Python, demonstrating efficient data handling.
- **Registration always assigns viewer role**, preventing privilege escalation. Only admins can promote users.
- **`create_all()`** is used instead of Alembic migrations, appropriate for the assessment scope.

## Assumptions

- Each user manages their own financial records. Viewers/Analysts see only their own data; Admins can view any record by ID.
- The `amount` field is always positive; the `type` field (income/expense) determines the financial direction.
- Categories are free-form strings (not a fixed enum), allowing flexibility for different users.
- The default admin account is seeded only when the database has no users, to ensure the system is immediately usable.
- JWT tokens expire after 30 minutes (configurable via environment variable).
- Only admins create financial records, reflecting a managed finance system where authorized personnel enter data. Viewers and analysts consume the data through views, summaries, and exports.
