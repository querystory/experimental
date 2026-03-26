# Sheet Webhook

Creates a Google Sheet + Apps Script webhook for collecting votes (or any POST data) without a backend.

## Setup

```bash
pip install google-api-python-client google-auth
gcloud auth application-default login
python setup.py --sheet-name "QR Code Votes"
```

This creates:
1. A Google Sheet with headers (Timestamp, File, Vote, Voter)
2. An Apps Script project bound to it with `doPost` and `doGet` endpoints
3. Shares with querystory.ai domain

You'll need to do the final deploy step manually in the Apps Script editor (the API can't fully automate this).

## Endpoints

**POST** — Record a vote:
```bash
curl -X POST https://script.google.com/macros/s/XXXXX/exec \
  -H 'Content-Type: application/json' \
  -d '{"file": "81_etched_solid_s.png", "vote": "up", "voter": "shapor"}'
```

**GET** — Retrieve aggregated votes:
```bash
curl https://script.google.com/macros/s/XXXXX/exec
# Returns: {"81_etched_solid_s.png": {"up": 5, "down": 1}, ...}
```

## Manual Setup (if you prefer)

1. Create a Google Sheet
2. Open Extensions > Apps Script
3. Paste the code from `setup.py` (the `APPS_SCRIPT_CODE` variable)
4. Deploy > New deployment > Web app > Anyone > Deploy
5. Copy the URL
