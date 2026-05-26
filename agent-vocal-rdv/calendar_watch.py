"""Sync annulations Google Calendar -> Airtable."""
from __future__ import annotations

import calendar_service
import airtable_service


def sync_recent_changes(minutes: int = 5) -> int:
    """Pour chaque event récemment modifié/supprimé, met à jour Airtable."""
    try:
        events = calendar_service.list_recent_events(minutes=minutes)
    except Exception as e:
        print(f"[watch] list error: {e}")
        return 0

    updated = 0
    for ev in events:
        event_id = ev.get("id")
        status = ev.get("status")
        if not event_id:
            continue
        row = airtable_service.get_by_event_id(event_id)
        if not row:
            continue
        current = row["fields"].get("Statut")
        if status == "cancelled" and current != "Annule":
            airtable_service.update_status(row["id"], "Annule")
            updated += 1
    return updated


if __name__ == "__main__":
    n = sync_recent_changes(minutes=60)
    print(f"Updated {n} rows.")
