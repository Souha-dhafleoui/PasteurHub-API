# PasteurHub API

PasteurHub is a RESTful API for travel health support. It provides:

- **Destination-based vaccine recommendations** (sourced from Institut Pasteur France – Pasteur.fr)
- **Symptom/exposure assessment** using a simple **Case-Based Reasoning (CBR)** approach
- **Staff-only management** (JWT-protected) for maintaining vaccines and cases
- A lightweight **frontend demo UI** served by Nginx
- Interactive API documentation via **Swagger UI**



## Features

### Public Features

- List travel destinations
- Get vaccine recommendations for a destination
- List vaccines (with price metadata when available)
- Run an assessment (CBR): submit a problem description → receive matched cases and suggested vaccines

### Staff-Only Features (JWT Required)

- Staff login → JWT token
- Create / Delete vaccines
- Create / Delete cases

---

## Tech Stack

| Component          | Technology                         |
| ------------------ | ---------------------------------- |
| **Backend**        | Python, FastAPI, Uvicorn           |
| **Database**       | PostgreSQL                         |
| **ORM**            | SQLAlchemy                         |
| **Authentication** | JWT (PyJWT) + password hashing     |
| **Deployment**     | Docker + Docker Compose            |
| **Frontend**       | Static HTML/CSS/JS served by Nginx |
| **Documentation**  | Swagger UI (`/docs`)               |

---

## 📁 Project Structure

```
pasteurhub-api/
├── README.md
├── COPILOT_USAGE.md                    # AI assistance documentation
├── docker-compose.yml                  # Multi-container orchestration
├── .gitignore
├── backend/
│   ├── requirements.txt                # Python dependencies
│   ├── Dockerfile                      # Backend container
│   ├── scripts/
│   │   └── seed_db.py                 # Database initialization
│   └── app/
│       ├── main.py                     # FastAPI application entry point
│       ├── resources/                  # API endpoints
│       │   ├── __init__.py
│       │   ├── auth.py                 # Authentication & authorization
│       │   ├── assessments.py          # Travel health assessments
│       │   ├── vaccines.py             # Vaccine management
│       │   ├── cases.py                # Case management (CBR)
│       │   ├── destinations.py         # Destination recommendations
│       │   └── router.py               # Route aggregation
│       ├── services/
│       │   ├── cbr.py                  # Case-based reasoning engine
│       │   └── travel_scraper.py       # Web scraper for Pasteur.fr
│       ├── models/
│       │   ├── vaccine.py
│       │   ├── case.py
│       │   ├── user.py
│       │   ├── destination.py
│       │   └── destination_vaccine.py
│       ├── schemas/
│       │   ├── assessment.py           # Request/response schemas
│       │   ├── auth.py
│       │   ├── case.py
│       │   ├── vaccine.py
│       │   └── travel.py
│       ├── core/
│       │   └── security.py             # JWT configuration
│       └── db/
│           ├── session.py              # Database session management
│           ├── init_db.py
│           └── base.py                 # SQLAlchemy base model
└── frontend/                           # Static files served by nginx
    ├── app.js
    ├── index.html
    └── styles.css
```

---

##  Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (1.29+)

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/yourusername/pasteurhub-api.git
cd pasteurhub-api
```

#### 2. Start containers

```bash
docker-compose up --build -d
```

This will start:

- **API server** on `http://localhost:8000`
- **PostgreSQL** database on port `5432`
- **Frontend UI** on `http://localhost:8501`

#### 3. Create database tables

```bash
docker-compose exec api python -c "from app.db.init_db import init_db; init_db()"
```

#### 4. Seed demo data

```bash
docker-compose exec api python scripts/seed_db.py
```

This will populate:

- Travel destinations (from Pasteur.fr)
- Vaccines with pricing metadata
- CBR cases for assessment
- Default staff account

#### 5. Access the application

- **Swagger UI (API Docs):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend Demo UI:** [http://localhost:8501](http://localhost:8501)

---

## Main Endpoints

### Public Endpoints

| Method | Endpoint                                       | Description                                        |
| ------ | ---------------------------------------------- | -------------------------------------------------- |
| `GET`  | `/resources/destinations`                      | List all travel destinations                       |
| `GET`  | `/resources/destinations/{id}/recommendations` | Get vaccine recommendations for a destination      |
| `GET`  | `/resources/vaccines`                          | List all vaccines with metadata                    |
| `POST` | `/resources/assessments`                       | Run CBR assessment (symptom → vaccine suggestions) |

### Protected Endpoints (Staff Only)

| Method   | Endpoint                   | Description                 |
| -------- | -------------------------- | --------------------------- |
| `POST`   | `/auth/login`              | Staff login (get JWT token) |
| `POST`   | `/resources/vaccines`      | Create new vaccine          |
| `DELETE` | `/resources/vaccines/{id}` | Delete vaccine by ID        |
| `POST`   | `/resources/cases`         | Create new CBR case         |
| `DELETE` | `/resources/cases/{id}`    | Delete case by ID           |

---

##  Database Schema

The PostgreSQL database contains the following tables:

### Core Tables

- **`users`** - Staff accounts (username, password_hash, role, created_at)
- **`vaccines`** - Vaccine catalog (name, price_tnd, currency, source_url, updated_at)
- **`destinations`** - Travel destinations (name, group_code, source_url)
- **`cases`** - CBR knowledge base (problem_text, scenario_type, vaccine_id)

### Relationships

- **`destination_vaccines`** - Many-to-many link between destinations and vaccines
  - Fields: `destination_id`, `vaccine_id`, `requirement_level` (required/recommended)

### Key Constraints

- **Primary Keys:** All main tables use `id` as primary key
- **Foreign Keys:** Enforce referential integrity across tables
- **Composite Keys:** `destination_vaccines` uses `(destination_id, vaccine_id)`

---

## Stopping the Application

```bash
docker-compose down
```

To also remove volumes (database data):

```bash
docker-compose down -v
```

---

## 👤 Author

**Souha Dhafleoui**

- Project Supervisor: Prof. Montassar Ben Messaoued
- Institution: Tunis Business School

---

<div align="center">

</div>
