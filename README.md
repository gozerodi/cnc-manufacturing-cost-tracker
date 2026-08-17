# CNC Manufacturing Cost Tracker

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-PySide6%20%28Qt%29-41CD52?style=flat-square&logo=qt&logoColor=white)
![Database](https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Domain](https://img.shields.io/badge/Domain-Manufacturing%20ERP-C0392B?style=flat-square)

`Libraries:` ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square) ![Alembic](https://img.shields.io/badge/Alembic-4B8BBE?style=flat-square) ![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=flat-square&logo=python&logoColor=white) ![bcrypt](https://img.shields.io/badge/bcrypt-8E44AD?style=flat-square) ![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white) ![PyInstaller](https://img.shields.io/badge/PyInstaller-2C3E50?style=flat-square)

A desktop ERP application for small CNC machining job shops, built to give shop owners a clear, per-process view of what each part actually costs to produce — and what it actually earns.

## The Problem

In a job shop, a single part often passes through several machines and operators before it's finished — turning, milling, grinding, and so on. Each of those steps has its own labor cost, machine time, tooling wear, and setup overhead. Without a system to track this, shop owners typically price jobs off gut feeling or a single blended margin, with no visibility into which specific processes are actually profitable and which are quietly eating the margin.

This application solves that by:

- Locking in **per-step cost snapshots** (labor rate, machine rate, tool cost) at the moment a work order is planned, so historical jobs stay accurate even after rates change later.
- Splitting the sale price into a **net price contribution per processing step**, proportional to how much time each step takes — so a shop can see exactly how much of a job's margin comes from turning vs. milling vs. finishing, for example.
- Tracking **planned vs. actual** processing time on every production entry and converting the deviation directly into a cost/gain figure.
- Rolling all of this up into cost, revenue, and performance dashboards by machine, customer, and time period.

## Key Features

- **Role-based access** — separate Admin and Staff logins with distinct menus and permissions.
- **Planning** — build a work order step by step (machine, operators, tools, processing time), with a live cost/price preview that recalculates as you edit.
- **Daily production entry** — log actual output per step per day; work orders auto-complete once the final step's quantity is fully produced.
- **Cost snapshot principle** — updating a machine's hourly rate or an employee's salary never rewrites the cost of work already planned or produced.
- **Analytics** — order tracking with step-by-step progress bars, planned-vs-actual deviation cost, machine performance, customer performance, and a revenue dashboard, all with day/week/month/quarter/year filtering.
- **Cost breakdown** — fixed and month-specific expenses, and a full cost pie chart (salaries, fixed costs, machine costs, one-off expenses) per month.
- **PDF daily reports** — one-click generation of a printable daily production summary.
- **Global error handling** — unhandled exceptions are caught, logged locally, and shown to the user without crashing the app.
- **Light/dark theme**, consistent across every screen.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| UI | [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python) |
| Theme | [pyqtdarktheme](https://github.com/5yutan5/PyQtDarkTheme) — dark/light/system |
| ORM | SQLAlchemy 2.x |
| Database | PostgreSQL, via psycopg2 |
| Migrations | Alembic |
| Charts | Matplotlib, embedded via `FigureCanvasQTAgg` |
| Auth | bcrypt password hashing |
| PDF export | Qt's `QPrinter` / `QTextDocument` |
| Packaging | PyInstaller (`--onedir`, for Windows distribution) |
| Testing | pytest |

## Architecture

```mermaid
flowchart TB
    subgraph UI["UI — app/ui (PySide6)"]
        Login["login_window.py"]
        Main["main_window.py"]
        Pages["pages/admin, pages/staff"]
        Widgets["widgets/ (tables, filters, inputs, cards)"]
    end

    subgraph SVC["Services — app/services (business logic)"]
        Cost["cost_service"]
        Planning["planning_service"]
        Production["production_service"]
        Analytics["analytics_service"]
        Report["report_service"]
        Other["customer / machine / personnel / tool / settings services"]
    end

    subgraph REPO["Repositories — app/repositories (plain DB access)"]
        Repos["work_order, machine, personnel, tool, customer,\ndaily_production, daily_report, expense repositories"]
    end

    subgraph MODEL["Models — app/models (SQLAlchemy ORM)"]
        Models["one file per table"]
    end

    subgraph CORE["Core — app/core"]
        Config["config.py"]
        DB["database.py (session)"]
        Security["security.py (bcrypt)"]
        ErrorHandler["error_handler.py"]
        TimeParser["time_parser.py"]
    end

    Postgres[("PostgreSQL")]
    Alembic["Alembic migrations"]

    Login --> Main
    Main --> Pages
    Pages --> Widgets
    Pages --> SVC
    SVC --> REPO
    REPO --> MODEL
    MODEL --> DB
    DB --> Postgres
    Alembic --> Postgres
    Config --> DB
    Security --> Login
    ErrorHandler -.-> Main
    TimeParser -.-> SVC
```

![CNC Cost Tracker architecture diagram](assets/architecture-diagram.svg)

```
app/
├── core/          # config loading, DB session, password hashing, error handling, time parsing
├── models/        # SQLAlchemy ORM models, one file per table
├── repositories/  # plain DB access (CRUD + queries) — no business logic
├── services/       # all business logic and calculations (cost, planning, production, analytics)
└── ui/
    ├── login_window.py, main_window.py
    ├── widgets/    # shared components (tables, time/money inputs, date filters...)
    └── pages/
        ├── admin/  # admin-only screens
        └── staff/  # staff screens
```

The UI never performs calculations directly — every number shown on screen comes from a service function, which keeps the business logic unit-testable independently of the Qt layer. Repositories are a thin data-access layer; nothing but plain queries lives there.

## Getting Started

### Prerequisites

- Python 3.11+
- A running PostgreSQL instance

### Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp config.example.ini config.ini
# edit config.ini with your PostgreSQL host/port/credentials

alembic upgrade head             # creates the schema
python scripts/seed.py           # creates demo login users
python main.py
```

### Demo logins

`scripts/seed.py` creates two accounts to explore the app with:

| Username | Password | Role |
|---|---|---|
| `admin1` | `admin123` | Admin |
| `staff1` | `staff123` | Staff |

The Personnel Setup page is additionally protected by a page-level password, `admin123` by default (changeable from within the page).

No business data (customers, machines, work orders, etc.) is seeded — the app starts empty so you can populate it with your own sample data.

### Running tests

```bash
pytest
```

## Future Work

- Further UI/UX polish across the analytics and planning screens.
- A tablet-optimized daily production entry screen, so operators can log output directly on the shop floor — replacing the paper production slips that most small shops still rely on today.

## License

MIT — see [LICENSE](LICENSE).
