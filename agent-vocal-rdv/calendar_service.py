"""Google Calendar — disponibilités, réservation, annulation."""
from __future__ import annotations

import base64
import json
import os
import uuid
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Any

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TZ = pytz.timezone(os.getenv("TIMEZONE", "Europe/Paris"))
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

TOKEN_PATH = Path("token.json")
CREDS_PATH = Path("credentials.json")


def _load_creds_from_env() -> Credentials | None:
    """Restaure les credentials depuis GOOGLE_TOKEN_JSON (base64) — pour Railway."""
    raw = os.getenv("GOOGLE_TOKEN_JSON")
    if not raw:
        return None
    try:
        data = json.loads(base64.b64decode(raw).decode())
    except Exception:
        try:
            data = json.loads(raw)
        except Exception:
            return None
    return Credentials.from_authorized_user_info(data, SCOPES)


def _materialize_credentials_file() -> Path | None:
    """Écrit credentials.json depuis GOOGLE_CREDENTIALS_JSON si absent."""
    if CREDS_PATH.exists():
        return CREDS_PATH
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not raw:
        return None
    try:
        decoded = base64.b64decode(raw).decode()
    except Exception:
        decoded = raw
    CREDS_PATH.write_text(decoded)
    return CREDS_PATH


def get_credentials() -> Credentials:
    creds = _load_creds_from_env()
    if creds is None and TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
        return creds

    creds_file = _materialize_credentials_file()
    if not creds_file:
        raise RuntimeError(
            "Aucun credentials.json ni GOOGLE_CREDENTIALS_JSON. "
            "Téléchargez OAuth desktop creds depuis Google Cloud Console."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def _service():
    return build("calendar", "v3", credentials=get_credentials(), cache_discovery=False)


# ---------- Disponibilités ----------

def _load_availability_ranges() -> list[dict]:
    """Plages depuis Airtable (Config table). Fallback : 9h-17h L-V."""
    try:
        from airtable_service import get_availability_ranges
        ranges = get_availability_ranges()
        if ranges:
            return ranges
    except Exception as e:
        print(f"[calendar] Airtable config indisponible : {e}")
    return [{"id": "default", "label": "Semaine", "jours": [0, 1, 2, 3, 4], "debut": 9, "fin": 17}]


def get_available_slots(days_ahead: int = 7, slot_minutes: int = 30) -> list[dict]:
    """Renvoie la liste des créneaux libres sur les N prochains jours."""
    svc = _service()
    now = datetime.now(TZ)
    start = now
    end = now + timedelta(days=days_ahead)

    body = {
        "timeMin": start.isoformat(),
        "timeMax": end.isoformat(),
        "timeZone": str(TZ),
        "items": [{"id": CALENDAR_ID}],
    }
    busy = svc.freebusy().query(body=body).execute()
    busy_periods = [
        (
            datetime.fromisoformat(p["start"].replace("Z", "+00:00")).astimezone(TZ),
            datetime.fromisoformat(p["end"].replace("Z", "+00:00")).astimezone(TZ),
        )
        for p in busy["calendars"][CALENDAR_ID]["busy"]
    ]

    ranges = _load_availability_ranges()
    slots: list[dict] = []

    for d in range(days_ahead + 1):
        day = (now + timedelta(days=d)).date()
        weekday = day.weekday()
        day_ranges = [r for r in ranges if weekday in r.get("jours", [])]
        if not day_ranges:
            continue

        for r in day_ranges:
            start_dt = TZ.localize(datetime.combine(day, time(int(r["debut"]), 0)))
            end_dt = TZ.localize(datetime.combine(day, time(int(r["fin"]), 0)))
            cursor = start_dt
            if cursor < now:
                # Arrondi au prochain quart d'heure futur
                delta = (now - cursor).total_seconds() / 60
                bump = int((delta // slot_minutes) + 1) * slot_minutes
                cursor = cursor + timedelta(minutes=bump)

            while cursor + timedelta(minutes=slot_minutes) <= end_dt:
                slot_end = cursor + timedelta(minutes=slot_minutes)
                overlap = any(b_start < slot_end and cursor < b_end for b_start, b_end in busy_periods)
                if not overlap:
                    slots.append({
                        "start": cursor.isoformat(),
                        "end": slot_end.isoformat(),
                        "label": cursor.strftime("%A %d %B à %Hh%M"),
                    })
                cursor = slot_end

    return slots


def format_slots_for_agent(slots: list[dict], limit: int = 8) -> dict:
    """Renvoie une version lisible + machine pour l'agent VAPI."""
    days_fr = {
        "Monday": "lundi", "Tuesday": "mardi", "Wednesday": "mercredi",
        "Thursday": "jeudi", "Friday": "vendredi", "Saturday": "samedi", "Sunday": "dimanche",
    }
    months_fr = {
        "January": "janvier", "February": "février", "March": "mars", "April": "avril",
        "May": "mai", "June": "juin", "July": "juillet", "August": "août",
        "September": "septembre", "October": "octobre", "November": "novembre", "December": "décembre",
    }

    sample = slots[:limit]
    human_lines = []
    for s in sample:
        dt = datetime.fromisoformat(s["start"])
        label = dt.strftime("%A %d %B à %Hh%M")
        for en, fr in {**days_fr, **months_fr}.items():
            label = label.replace(en, fr)
        human_lines.append(label)

    return {
        "lisible": "Voici les créneaux disponibles : " + "; ".join(human_lines) if human_lines else "Aucun créneau disponible.",
        "creneaux": sample,
    }


# ---------- Réservation / annulation ----------

def book_appointment(
    start_iso: str,
    end_iso: str,
    summary: str,
    description: str,
    attendee_email: str | None = None,
) -> dict:
    svc = _service()
    event_body: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso, "timeZone": str(TZ)},
        "end": {"dateTime": end_iso, "timeZone": str(TZ)},
        "reminders": {"useDefault": True},
    }
    if attendee_email:
        event_body["attendees"] = [{"email": attendee_email}]

    event = svc.events().insert(
        calendarId=CALENDAR_ID,
        body=event_body,
        sendUpdates="all" if attendee_email else "none",
    ).execute()
    return event


def cancel_event(event_id: str) -> bool:
    svc = _service()
    try:
        svc.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            sendUpdates="all",
        ).execute()
        return True
    except Exception as e:
        print(f"[calendar] cancel_event error: {e}")
        return False


# ---------- Watch (notifications) ----------

def start_watch(webhook_url: str) -> dict | None:
    svc = _service()
    body = {
        "id": str(uuid.uuid4()),
        "type": "web_hook",
        "address": webhook_url,
    }
    try:
        return svc.events().watch(calendarId=CALENDAR_ID, body=body).execute()
    except Exception as e:
        print(f"[calendar] start_watch error: {e}")
        return None


def list_recent_events(minutes: int = 5) -> list[dict]:
    svc = _service()
    now = datetime.now(TZ)
    updated_min = (now - timedelta(minutes=minutes)).isoformat()
    res = svc.events().list(
        calendarId=CALENDAR_ID,
        updatedMin=updated_min,
        showDeleted=True,
        singleEvents=True,
    ).execute()
    return res.get("items", [])
