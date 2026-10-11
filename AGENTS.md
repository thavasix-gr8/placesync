# PlaceSync: instructions for Codex

Read this whole file before changing anything.

## 1. Project

PlaceSync is a placement drive and eligibility management platform for a college.

Problem: placement drives are handled through WhatsApp, Google Forms and Excel. Students miss deadlines, and coordinators check CGPA, arrears, department and batch by hand, which causes mistakes.

Solution: one web app. Admins post drives with eligibility rules. The system checks each student against the rules automatically, shows only the drives a student qualifies for, and shows the reason for the ones they do not qualify for. Students apply with one click. Admins update the status of each application.

Roles:
- student: profile, eligible drives with reasons, apply, track status
- admin: create drives, view applicants, update status, see stats

The selling point is the eligibility engine plus the "reason shown when not eligible". Make that very visible in the UI.

## 2. Who I am building for

I am a B.Tech IT student. I must explain every file to my teacher in a viva and the submission is soon, so:
- write simple, student-friendly code, as if a student wrote it
- no clever abstractions, no advanced patterns, no unnecessary libraries
- short comments only where they help understanding
- tell me the file name for every file you create or change, with a one-line explanation
- keep answers short and direct, in British English

## 3. Environment

- Ubuntu 24.04, zsh, VS Code, about 8 GB RAM. Keep everything lightweight.
- Everything must be free and open source. No paid APIs, no cloud services.
- Python packages go inside a venv at backend/venv only. Never use --break-system-packages and never install system-wide.
- Backend commands run inside backend/ with the venv active: source venv/bin/activate
- Run backend: uvicorn app.main:app --reload (port 8000)
- Run frontend: npm run dev inside frontend/ (Vite, port 5173). CORS must allow http://localhost:5173.
- Never delete the database, venv, or Git history. Never run destructive commands without asking me.
- Secrets stay out of code. SECRET_KEY is read from the environment.
- Never claim something works or a test passed unless you actually ran it and saw the output. If you could not run it, say so.

## 4. Stage 1 and 2 design (build this first if it does not exist yet)

Folder: placesync/backend/app/

- database.py: SQLite engine (sqlite:///./placesync.db, check_same_thread False), SessionLocal, Base, get_db()
- models.py: tables User, Drive, Application
  - User: id, name, email (unique), password_hash, role ("student" or "admin"), register_number, department, batch, cgpa, arrears
  - Drive: id, company, job_role, description, deadline, min_cgpa, max_arrears, allowed_departments (comma separated string, empty means all), batch
  - Application: id, student_id, drive_id, status, applied_at
- schemas.py: SignupRequest (password min 6, cgpa 0 to 10, arrears at least 0), UserOut (never returns the password)
- auth.py: hash_password, verify_password (bcrypt), create_token (PyJWT, HS256, 8 hours, stores user id and role), get_current_user, require_admin, require_student, OAuth2PasswordBearer with tokenUrl "/login"
- main.py: creates tables, CORS for http://localhost:5173, routes /, /signup (students only), /login (form data, username is the email), /me, /admin/check
- seed_admin.py: creates admin@placesync.com with password admin123 (demo only)

Only change these files when needed for a new feature. Do not change the models without telling me why.

## 5. Work to do, in this order

Finish each stage, test it, and tell me honestly what passed before starting the next.

### Stage 3: drives and the eligibility engine (backend)
1. New file app/eligibility.py with check_eligibility(student, drive) returning (is_eligible, reasons).
   Rules:
   - student CGPA must be at least min_cgpa
   - student arrears must not exceed max_arrears
   - student department must be in allowed_departments (skip if empty)
   - student batch must equal batch (skip if the drive batch is empty)
   - the deadline must not have passed
   Reasons must be readable, for example: CGPA 6.9 is below the required 7.5
2. Routes (put them in a new app/routes_drives.py router and include it in main.py):
   - POST /drives (admin)
   - GET /drives: for a student, return every drive with eligible (true or false) and reasons; for an admin, return all drives
   - PUT /drives/{id} and DELETE /drives/{id} (admin)
3. PUT /me: a student can update department, batch, CGPA and arrears (eligibility depends on them).
4. Remove the test route /admin/check.

### Stage 4: applications (backend)
- POST /drives/{id}/apply (student): only if eligible, only once per drive, only before the deadline
- GET /applications/me (student): own applications with drive details
- GET /drives/{id}/applications (admin): applicants with student details
- PUT /applications/{id}/status (admin): Applied, Shortlisted, Rejected, Selected
- GET /admin/stats (admin): total drives, total applications, shortlisted, selected
- Add pytest tests for eligibility.py (passing, failing on each rule, and combined failures).

### Stage 5: frontend setup
- Create frontend/ with Vite + React.
- Install only: react-router-dom, tailwindcss (with its Vite plugin), lucide-react.
- Use fetch, not axios. Keep the API base URL in one file (src/api.js).
- Store the JWT and role in localStorage. Add a ProtectedRoute that checks login and role.
- Build the shared components first: Button, Card, Badge, Navbar, Sidebar, Toast, Skeleton, EmptyState.

### Stage 6: student pages
- Login and Signup
- Dashboard with stat cards (Eligible drives, Applied, Shortlisted)
- Drives list: company cards with role, deadline and the rules as chips. Eligible drives get an "Eligible" badge and an Apply button. Ineligible drives are dimmed and show the reasons in red. This is the most important screen.
- My applications with a status badge or timeline
- Profile page (edit CGPA, arrears, department, batch)

### Stage 7: admin pages
- Dashboard with stat cards and a recent drives table
- Create drive form with the four eligibility fields grouped together
- Applicants table per drive with a status dropdown on each row (badge colour changes as the status changes)
- Edit and delete drives

### Stage 8: finish
- Write README.md: features, architecture, setup, run, test, screenshots placeholder, honest limitations
- Add .env.example with SECRET_KEY=
- Give me the exact Git commands to publish to GitHub

## 6. Theme: dark neon (same as my VEHISOUND app)

Dark mode only. No light mode.

Colours:
- page background: #0a0a0a
- card background: #111111
- card border: 1px solid, accent colour at about 20 to 30 percent opacity
- text: white for headings, grey (#9ca3af) for secondary text
- primary accent: cyan #00fff7
- secondary accent: purple #a855f7

Status colours:
- Applied: cyan #00fff7
- Shortlisted: amber #eab308
- Selected and Eligible: green #22c55e
- Rejected and Not eligible: red #ef4444
- Other accents if needed: orange #f97316, blue #3b82f6

Style rules:
- thin 0.5 to 1px borders in the accent colour
- soft glow on hover: box-shadow with the accent colour at about 15 to 25 percent opacity
- accent fills at about 15 percent opacity (for example a badge has a 15 percent tinted background with a full-colour border and text)
- subtle grid or divider lines at about 8 percent opacity
- rounded corners, simple line icons from lucide-react
- font: Inter for text, a monospace font for numbers and stats
- the login page is a split screen: neon gradient panel with the tagline on the left, form on the right
- extras: loading skeletons, toast messages, friendly empty states, responsive layout (works on a phone)
- keep it clean. Do not add heavy animations or large images.

## 7. Definition of done

- backend runs and every route works on /docs
- frontend talks to the backend and all roles work
- tests for the eligibility engine pass
- README is complete and honest
- I can explain every file
