# Code Sprint – TechTorrent 2K26

Production-ready department-level coding contest platform built with Flask.

## Folder Structure

```
.
├── app/
│   ├── __init__.py
│   ├── execution.py
│   ├── models.py
│   ├── routes.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/anti_cheat.js
│   └── templates/
├── instance/
├── requirements.txt
└── run.py
```

## Setup

1. `python3 -m venv .venv`
2. `source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`)
3. `pip install -r requirements.txt`
4. Ensure `gcc` is installed and available in PATH.
5. `python run.py`

First run auto-creates admin accounts:
- `admin1@codesprint.com` / `Admin@123`
- `admin2@codesprint.com` / `Admin@456`

## Database Schema

Tables:
- `user`: participants and admins.
- `contest`: contest status and schedule.
- `problem`: question definitions.
- `hidden_test_case`: hidden evaluator data.
- `submission`: all attempts and verdicts.
- `violation`: anti-cheat event logs.

SQLite DB path: `instance/codesprint.db`.

## LAN Deployment

- Run on host machine with `python run.py`.
- Access from clients via `http://SERVER_IP:5000`.
- Keep `debug=False` in production.

## Firewall Instructions

### Windows
- Open `Windows Defender Firewall` → Inbound Rules → New Rule.
- Port → TCP → `5000` → Allow.

### macOS
- System Settings → Network → Firewall → Options.
- Allow incoming connections for Python.

## Pre-Contest Testing Checklist

- [ ] Both pre-created admin accounts can login.
- [ ] Student registration/login works.
- [ ] Admin can add/edit/delete problems and hidden tests.
- [ ] Start contest blocks/unblocks submissions correctly.
- [ ] Python and C submissions return expected verdicts.
- [ ] Infinite-loop submission hits TLE.
- [ ] Compilation errors are reported.
- [ ] Violation logs appear in admin dashboard.
- [ ] Leaderboard visible to admins and blocked for students.
- [ ] CSV export downloads valid data.
- [ ] 10+ concurrent submissions tested in LAN dry-run.
