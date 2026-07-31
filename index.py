from flask import Flask, request, jsonify
from google.oauth2.service_account import Credentials
import gspread
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")


def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Accept",
    }


def get_sheets_client():
    if not GOOGLE_CREDENTIALS:
        raise ValueError("GOOGLE_CREDENTIALS environment variable is not set.")
    creds_info = json.loads(GOOGLE_CREDENTIALS)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(credentials)


def parse_form_data():
    data = {}
    for key in request.form.keys():
        values = request.form.getlist(key)
        if len(values) > 1:
            data[key] = ", ".join(values)
        else:
            data[key] = values[0] if values else ""
    return data


def get_or_create_worksheet(spreadsheet, title):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=60)


def append_row_with_headers(worksheet, data):
    headers = worksheet.row_values(1)
    if not headers:
        headers = list(data.keys())
        worksheet.append_row(headers)
    row = [data.get(h, "") for h in headers]
    worksheet.append_row(row)


# ═══════════════════════════════════════════════════════════
# ROUTES: NO /api/ prefix — Vercel auto-routes api/index.py to /api
# So /submit handles requests to /api/submit
# And /health handles requests to /api/health
# ═══════════════════════════════════════════════════════════

@app.route("/submit", methods=["POST", "OPTIONS"])
def submit():
    if request.method == "OPTIONS":
        return "", 204, get_cors_headers()

    try:
        data = parse_form_data()
        campaign = data.get("campaign", "general")
        data["submission_timestamp"] = datetime.now(timezone.utc).isoformat()

        client = get_sheets_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = get_or_create_worksheet(spreadsheet, campaign)
        append_row_with_headers(worksheet, data)

        return (
            jsonify({"success": True, "message": "Assessment submitted successfully"}),
            200,
            get_cors_headers(),
        )

    except Exception as e:
        return (
            jsonify({"success": False, "error": str(e)}),
            500,
            get_cors_headers(),
        )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


# Local development entry point
if __name__ == "__main__":
    app.run(debug=True)
