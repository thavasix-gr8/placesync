# PlaceSync

PlaceSync is a college placement drive and eligibility management web app. It replaces placement updates spread across WhatsApp, Google Forms and spreadsheets with one system for students and admins.

The main feature is the eligibility engine. Students see every drive, whether they qualify, and a clear reason when they do not.

## Features

### Student

- Create an account and sign in.
- Update department, batch, CGPA and arrears.
- See placement drives with eligibility result and readable reasons.
- Apply once to eligible drives before the deadline.
- Track application status: Applied, Shortlisted, Rejected or Selected.

### Admin

- Sign in with the demo admin account.
- Create, edit and delete placement drives.
- Set CGPA, arrears, department and batch eligibility rules.
- View applicants for each drive.
- Update application status.
- View counts for drives, applications, shortlisted and selected students.

## Architecture

```text
React + Vite frontend (port 5173)
          |
          | fetch and JWT bearer token
          v
FastAPI backend (port 8000)
          |
          v
SQLite database (backend/placesync.db)
```

- `backend/app/` contains the FastAPI routes, authentication, models and eligibility engine.
- `backend/tests/` contains the eligibility engine tests.
- `frontend/src/` contains React pages, shared components, API helper and styles.

## Setup

### Backend

From the project folder:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="replace-this-with-a-long-random-value"
python -m app.seed_admin
uvicorn app.main:app --reload
```

The API documentation is available at <http://localhost:8000/docs>.

Demo admin account:

```text
Email: admin@placesync.com
Password: admin123
```

This account is for local demonstration only.

### Frontend

Use Node.js 20 or newer because the installed Tailwind Vite plugin requires it.

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

## Run tests

```bash
cd backend
source venv/bin/activate
pytest -q
```

The eligibility test suite covers a passing student, each failing rule, and combined failures.

## Screenshots

Add screenshots here before submission:

- Student eligible drives screen
- Student ineligible reason screen
- Admin drive creation screen
- Admin applicants screen

## Honest limitations

- The database is SQLite, so this is suitable for a college project/demo rather than large production use.
- There is no email verification, password reset or notification system.
- The frontend build was attempted with Node.js 18.19.1 in this environment and failed before compiling because `@tailwindcss/vite` requires Node.js 20+. It should be run with Node.js 20 or newer.
- The application uses local browser storage for JWTs, which is suitable for this project but not a production security design.
