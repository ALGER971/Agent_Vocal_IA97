"""Crée les tables Airtable (Rendez-vous + Config) via l'API Meta. À lancer une fois."""
from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Rendez-vous")
CONFIG_TABLE = os.getenv("AIRTABLE_CONFIG_TABLE", "Config")

if not API_KEY or not BASE_ID:
    print("❌ AIRTABLE_API_KEY et AIRTABLE_BASE_ID requis.")
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
META_URL = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables"


def list_tables() -> list[dict]:
    r = requests.get(META_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("tables", [])


def create_table(name: str, fields: list[dict]) -> dict:
    r = requests.post(META_URL, headers=HEADERS, json={"name": name, "fields": fields}, timeout=30)
    if not r.ok:
        print(f"❌ {name}: {r.status_code} {r.text}")
        sys.exit(1)
    print(f"✅ Table {name} créée")
    return r.json()


RDV_FIELDS = [
    {"name": "Prenom", "type": "singleLineText"},
    {"name": "Nom", "type": "singleLineText"},
    {"name": "Email", "type": "email"},
    {"name": "Date RDV", "type": "singleLineText"},
    {"name": "Besoin", "type": "multilineText"},
    {
        "name": "Statut",
        "type": "singleSelect",
        "options": {"choices": [{"name": "Confirme"}, {"name": "Annule"}, {"name": "Termine"}]},
    },
    {"name": "Cree le", "type": "singleLineText"},
    {"name": "Call ID", "type": "singleLineText"},
    {"name": "Calendar Event ID", "type": "singleLineText"},
]

CONFIG_FIELDS = [
    {"name": "Cle", "type": "singleLineText"},
    {"name": "Valeur", "type": "multilineText"},
]


def main():
    existing = {t["name"] for t in list_tables()}
    if TABLE_NAME not in existing:
        create_table(TABLE_NAME, RDV_FIELDS)
    else:
        print(f"= Table {TABLE_NAME} existe déjà")
    if CONFIG_TABLE not in existing:
        create_table(CONFIG_TABLE, CONFIG_FIELDS)
    else:
        print(f"= Table {CONFIG_TABLE} existe déjà")


if __name__ == "__main__":
    main()
