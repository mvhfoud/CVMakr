"""Google Drive and Sheets integration helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

import gspread
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

CLIENT_SECRETS_FILE = os.getenv("CLIENT_SECRETS_FILE")
TOKEN_PATH = Path("token.json")
SHEET_ID = os.getenv("SHEET_ID")
FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")


def oauth_creds() -> Credentials:
    """Return cached OAuth credentials, refreshing or initiating auth if required."""

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def ensure_google_credentials() -> Credentials:
    """
    Validate credentials eagerly so the user is prompted before the main flow.
    """

    return oauth_creds()


def init_services() -> Tuple[any, gspread.Client]:
    """Instantiate Drive and Sheets clients ready for use."""

    creds = oauth_creds()
    drive_service = build("drive", "v3", credentials=creds)
    sheets_client = gspread.authorize(creds)
    return drive_service, sheets_client


def upload_to_drive(file_path: Path, folder_id: str | None = None) -> None:
    """Upload a generated file to Google Drive."""

    drive_service, _ = init_services()
    target_folder = folder_id or FOLDER_ID
    metadata = {
        "name": file_path.name,
        "parents": [target_folder],
    } if target_folder else {"name": file_path.name}
    media = MediaFileUpload(str(file_path), mimetype="text/plain")
    drive_service.files().create(body=metadata, media_body=media, fields="id").execute()


def append_to_sheet(row: List[str], sheet_id: str | None = None) -> None:
    """
    Append a row to Google Sheets with formatting parity to the legacy behaviour.
    """

    _, sheets_client = init_services()
    sheet = sheets_client.open_by_key(sheet_id or SHEET_ID).sheet1
    sheet.append_row(row, value_input_option="USER_ENTERED")

    all_values = sheet.get_all_values()
    row_idx = len(all_values)
    cell_label = f"B{row_idx}"
    sheet.format(cell_label, {"textFormat": {"bold": True}})


def mount_drive() -> Path:
    """Mirror the legacy mount helper (used for Streamlit deployments)."""

    return Path(os.getcwd())
