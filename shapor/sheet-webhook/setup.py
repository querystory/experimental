#!/usr/bin/env python3
"""
Create a Google Sheet + Apps Script webhook for collecting votes.

Usage:
    python setup.py --sheet-name "QR Code Votes"

Creates:
1. A Google Sheet with headers
2. An Apps Script project attached to it with a doPost webhook
3. Deploys the script as a web app
4. Prints the webhook URL

Requires: pip install google-api-python-client google-auth
Uses application default credentials (gcloud auth application-default login).
"""

import argparse
import json
import sys

from google.auth import default
from googleapiclient.discovery import build


APPS_SCRIPT_CODE = """
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  // Supports: vote="up"/"down" or stars=1-5 (or both)
  sheet.appendRow([
    new Date(),
    data.file,
    data.vote || "",
    data.stars || "",
    data.voter || "anonymous"
  ]);
  return ContentService.createTextOutput(JSON.stringify({ok: true}))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = sheet.getDataRange().getValues();
  var votes = {};
  for (var i = 1; i < data.length; i++) {
    var file = data[i][1];
    var vote = data[i][2];
    var stars = data[i][3];
    if (!votes[file]) votes[file] = {up: 0, down: 0, stars: [], avg: 0};
    if (vote === "up") votes[file].up++;
    else if (vote === "down") votes[file].down++;
    if (stars) votes[file].stars.push(Number(stars));
  }
  // Calculate averages
  for (var f in votes) {
    var s = votes[f].stars;
    votes[f].avg = s.length ? Math.round(s.reduce(function(a,b){return a+b},0) / s.length * 10) / 10 : 0;
    votes[f].count = s.length;
  }
  return ContentService.createTextOutput(JSON.stringify(votes))
    .setMimeType(ContentService.MimeType.JSON);
}
""".strip()


def main():
    parser = argparse.ArgumentParser(description="Create a Google Sheet + Apps Script webhook")
    parser.add_argument("--sheet-name", default="QR Code Votes", help="Name for the Google Sheet")
    parser.add_argument("--domain", default="querystory.ai", help="Domain to share with (or 'none')")
    args = parser.parse_args()

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/script.projects",
    ]
    creds, project = default(scopes=scopes)

    # 1. Create the sheet
    sheets_svc = build("sheets", "v4", credentials=creds)
    result = sheets_svc.spreadsheets().create(body={
        "properties": {"title": args.sheet_name},
        "sheets": [{"properties": {"title": "Votes"}}],
    }).execute()
    sheet_id = result["spreadsheetId"]
    print(f"Sheet created: https://docs.google.com/spreadsheets/d/{sheet_id}")

    # Add headers
    sheets_svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Votes!A1:E1",
        valueInputOption="RAW",
        body={"values": [["Timestamp", "File", "Vote", "Stars", "Voter"]]},
    ).execute()

    # 2. Share with domain
    if args.domain != "none":
        drive_svc = build("drive", "v3", credentials=creds)
        drive_svc.permissions().create(
            fileId=sheet_id,
            body={"type": "domain", "domain": args.domain, "role": "writer"},
        ).execute()
        print(f"Shared with {args.domain}")

    # 3. Create Apps Script project bound to the sheet
    script_svc = build("script", "v1", credentials=creds)
    script_project = script_svc.projects().create(body={
        "title": f"{args.sheet_name} Webhook",
        "parentId": sheet_id,
    }).execute()
    script_id = script_project["scriptId"]
    print(f"Script project: https://script.google.com/d/{script_id}/edit")

    # 4. Push the code
    script_svc.projects().updateContent(
        scriptId=script_id,
        body={
            "files": [
                {
                    "name": "Code",
                    "type": "SERVER_JS",
                    "source": APPS_SCRIPT_CODE,
                },
                {
                    "name": "appsscript",
                    "type": "JSON",
                    "source": json.dumps({
                        "timeZone": "America/Los_Angeles",
                        "dependencies": {},
                        "webapp": {
                            "access": "ANYONE_ANONYMOUS",
                            "executeAs": "USER_DEPLOYING",
                        },
                        "exceptionLogging": "STACKDRIVER",
                        "runtimeVersion": "V8",
                    }),
                },
            ],
        },
    ).execute()
    print("Code pushed to Apps Script")

    # 5. Deploy as web app
    deployment = script_svc.projects().deployments().create(
        scriptId=script_id,
        body={
            "versionNumber": 1,
            "description": "Vote webhook",
            "manifestFileName": "appsscript",
        },
    ).execute()

    # Note: The Apps Script API deployment doesn't directly give the /exec URL.
    # The user needs to do the final deploy step manually from the editor.
    print(f"\nAlmost done! Open the script editor and deploy manually:")
    print(f"  https://script.google.com/d/{script_id}/edit")
    print(f"  Deploy > New deployment > Web app > Anyone > Deploy")
    print(f"  Copy the URL (https://script.google.com/macros/s/.../exec)")
    print(f"\nOr if the API deployment worked, check:")
    print(f"  Deployment ID: {deployment.get('deploymentId', 'unknown')}")


if __name__ == "__main__":
    main()
