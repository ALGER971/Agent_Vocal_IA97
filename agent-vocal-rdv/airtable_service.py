"""Airtable — table Rendez-vous + table Config."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from pyairtable import Api

API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Rendez-vous")
CONFIG_TABLE = os.getenv("AIRTABLE_CONFIG_TABLE", "Config")


def _api() -> Api:
    if not API_KEY or not BASE_ID:
        raise RuntimeError("AIRTABLE_API_KEY ou AIRTABLE_BASE_ID manquant.")
    return Api(API_KEY)


def _table():
    return _api().table(BASE_ID, TABLE_NAME)


def _config_table():
    return _api().table(BASE_ID, CONFIG_TABLE)


# ---------- Rendez-vous ----------

def create_appointment(
    prenom: str,
    nom: str,
    email: str,
    date_rdv: str,
    besoin: str,
    call_id: str | None = None,
    calendar_event_id: str | None = None,
    statut: str = "Confirme",
) -> dict:
    fields = {
        "Prenom": prenom,
        "Nom": nom,
        "Email": email,
        "Date RDV": date_rdv,
        "Besoin": besoin,
        "Statut": statut,
        "Cree le": datetime.utcnow().isoformat(),
    }
    if call_id:
        fields["Call ID"] = call_id
    if calendar_event_id:
        fields["Calendar Event ID"] = calendar_event_id
    return _table().create(fields)


def list_appointments() -> list[dict]:
    return _table().all(sort=["-Cree le"])


def update_status(record_id: str, statut: str) -> dict:
    return _table().update(record_id, {"Statut": statut})


def get_by_event_id(event_id: str) -> dict | None:
    rows = _table().all(formula=f"{{Calendar Event ID}} = '{event_id}'", max_records=1)
    return rows[0] if rows else None


# ---------- Config (plages de disponibilité) ----------

AVAILABILITY_KEY = "availability_ranges"


def get_availability_ranges() -> list[dict]:
    rows = _config_table().all(formula=f"{{Cle}} = '{AVAILABILITY_KEY}'", max_records=1)
    if not rows:
        return []
    try:
        return json.loads(rows[0]["fields"].get("Valeur", "[]"))
    except Exception:
        return []


def save_availability_ranges(ranges: list[dict]) -> dict:
    rows = _config_table().all(formula=f"{{Cle}} = '{AVAILABILITY_KEY}'", max_records=1)
    payload = {"Cle": AVAILABILITY_KEY, "Valeur": json.dumps(ranges, ensure_ascii=False)}
    if rows:
        return _config_table().update(rows[0]["id"], {"Valeur": payload["Valeur"]})
    return _config_table().create(payload)
