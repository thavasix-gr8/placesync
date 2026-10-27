# PlaceSync

PlaceSync is a college placement drive and eligibility management web app. It replaces placement updates spread across WhatsApp, Google Forms and spreadsheets with one system for students and the placement cell (admin).

The main feature is the eligibility engine. Students see every drive, whether they qualify, and a clear reason when they do not.

## Features

### Student

- Create an account and sign in with email and password, or link and sign in with an SSN Microsoft account.
- Update department, batch, CGPA and arrears, with a profile completeness bar.
- Change password from the profile page.
- Upload a PDF resume (maximum 10 MB), view it and replace it.
- Search drives by company or role and filter them (all, eligible only, closing in 7 days, deadline passed).
- See every drive with the eligibility result and readable reasons (CGPA, arrears, department, batch).
- Apply once to an eligible drive before the deadline. After the deadline the button shows "Applications closed".
- Applying attaches the current resume to that application in one step.
- Track each application with a status step bar: Applied, Shortlisted, Selected or Rejected.
- Get in-app notifications when the admin changes an application status.
- Read announcements from the placement cell on the dashboard, with a popup for the full message.

### Admin (placement cell)

- Sign in with the demo admin account.
- Create, edit and delete placement drives with CGPA, arrears, department and batch rules.
- Open a separate Applicants page to review applicants for any drive.
- View or download each applicant's resume (the version submitted with the application).
- Export the applicant list as a CSV file.
- Download all applicant resumes for a drive as one ZIP file.
- Filter applicants by status and change the status of several applicants at once.
- Post and delete announcements, optionally linked to a drive.
- See counts for drives, applications, shortlisted and selected students.

## How the placement cell uses it

1. The admin posts a drive and students apply.
2. After the deadline the admin exports the CSV and the resume ZIP and sends them to the company outside the app. PlaceSync never emails resumes.
3. Company tests and interviews happen outside the app.
4. The admin updates each student's status in PlaceSync, and students see the result as a status change and a notification.

## Architecture

```text
React + Vite frontend (port 5173)
          |
          | fetch and JWT bearer token
          v
FastAPI backend (port 8000)
          |
          +--> SQLite database (backend/placesync.db)
          +--> Private resume storage (backend/private_uploads)
          +--> Microsoft Entra ID (ID token validation)
```

- `backend/app/` contains the FastAPI routes, authentication, Microsoft login, resume handling, models, migrations and the eligibility engine.
- `backend/tests/` contains the automated tests.
- `frontend/src/` contains React pages, shared components, the API helper, Microsoft sign-in code and styles.

## Security design

- Passwords are stored as hashes. Sessions use JWT bearer tokens, and roles are checked on the backend for every protected route.
- Microsoft login uses a single-tenant Entra app. The backend validates the ID token signature, audience, issuer, expiry, tenant and nonce.
- A Microsoft account is linked by tenant ID and object ID, never by email alone. Linking needs the existing PlaceSync password. Microsoft login never creates accounts and never grants admin rights.
- No client secret is used in the React app.
- Resumes are PDF only, at most 10 MB, checked by file signature and size on the backend.
- Resumes are stored outside the public frontend folder under random file names. Every view or download is permission checked: a student sees only their own resume, and an admin sees only applicants of their own drives.
- Each application keeps the resume version submitted with it, so replacing a resume later does not change old applications.
- CSV export escapes cells that could run as spreadsheet formulas.
- Database changes are additive migrations that preserve existing data. Database backups, `.env` files and uploaded resumes are ignored by Git.

## Setup

### Backend

From the project folder:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
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

### Microsoft login (optional)

Password login works without any Microsoft settings. To enable Microsoft login:

1. Register a single-tenant app in Microsoft Entra with the Single-page application redirect URI `http://localhost:5173/login`.
2. In `backend/.env` set `ENTRA_CLIENT_ID` and `ENTRA_TENANT_ID`.
3. In `frontend/.env.local` set `VITE_ENTRA_CLIENT_ID` and `VITE_ENTRA_TENANT_ID`.
4. Restart both servers. Vite reads `.env.local` only at start-up.

Never commit `.env` or `.env.local`.

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

The tests cover the eligibility engine, Microsoft login (with mocked tokens), resume upload and access control, exports, bulk status changes, notifications, announcements, deadline checks and database migrations that preserve existing data.

## Screenshots

Add screenshots here before submission:

- Student eligible drives screen
- Student ineligible reason screen
- Student profile with resume upload
- Student dashboard with notifications and announcements
- Admin drive creation screen
- Admin applicants screen with resume buttons and export
- Admin announcement form

## Honest limitations

- The database is SQLite, so this is suitable for a college project or demo rather than large production use.
- Notifications and announcements appear inside the app only. There is no email or SMS sending, no email verification and no password reset by email.
- Microsoft login was tested live by hand on a local setup. The automated tests use mocked tokens.
- Company tests and interviews are not run inside PlaceSync. The admin only records the result as a status.
- Resumes are stored on the local disk of the backend machine, which is suitable for a demo but not for several servers.
- The application uses local browser storage for JWTs, which is suitable for this project but not a production security design.

## Future scope

- AI resume builder and drive-specific resume suggestions.
- Round tracker (aptitude, technical, HR) for each application.
- One-offer rule once a student is selected.
- Placement statistics charts and a separate company login.
