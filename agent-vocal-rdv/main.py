"""Serveur webhook FastAPI — reçoit les tool-calls VAPI."""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

import calendar_service
import airtable_service
from calendar_watch import sync_recent_changes
from dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        gc_hook = webhook_url.rsplit("/", 1)[0] + "/google-calendar-webhook"
        try:
            calendar_service.start_watch(gc_hook)
            print(f"[startup] Calendar watch -> {gc_hook}")
        except Exception as e:
            print(f"[startup] watch error: {e}")
    yield


app = FastAPI(title="Agent Vocal RDV", lifespan=lifespan)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return {"status": "Agent Vocal RDV actif"}


@app.get("/debug/calendar")
def debug_calendar():
    try:
        slots = calendar_service.get_available_slots(days_ahead=7)
        return {"ok": True, "slots": len(slots), "preview": slots[:3]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------- Outils VAPI ----------

def tool_verifier_disponibilites(args: dict) -> str:
    days = int(args.get("jours", 7))
    slots = calendar_service.get_available_slots(days_ahead=days)
    formatted = calendar_service.format_slots_for_agent(slots, limit=8)
    return json.dumps(formatted, ensure_ascii=False)


def tool_reserver_creneau(args: dict, call_id: str | None = None) -> str:
    start_iso = args["start"]
    end_iso = args["end"]
    prenom = args.get("prenom", "").strip()
    nom = args.get("nom", "").strip()
    email = args.get("email", "").strip()
    besoin = args.get("besoin", "").strip()

    company = os.getenv("COMPANY_NAME", "RDV")
    summary = f"RDV {prenom} {nom} — {company}"
    description = f"Besoin : {besoin}\nEmail : {email}\nCall ID : {call_id or ''}"

    event = calendar_service.book_appointment(
        start_iso=start_iso,
        end_iso=end_iso,
        summary=summary,
        description=description,
        attendee_email=email or None,
    )

    try:
        airtable_service.create_appointment(
            prenom=prenom,
            nom=nom,
            email=email,
            date_rdv=start_iso,
            besoin=besoin,
            call_id=call_id,
            calendar_event_id=event.get("id"),
        )
    except Exception as e:
        print(f"[reserver] airtable error: {e}")

    return json.dumps({
        "ok": True,
        "event_id": event.get("id"),
        "message": f"Rendez-vous confirmé pour {prenom} {nom} le {start_iso}.",
    }, ensure_ascii=False)


def dispatch_tool(name: str, args_str: str, call_id: str | None) -> str:
    try:
        args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
    except Exception:
        args = {}
    if name == "verifier_disponibilites":
        return tool_verifier_disponibilites(args)
    if name == "reserver_creneau":
        return tool_reserver_creneau(args, call_id=call_id)
    return json.dumps({"error": f"Outil inconnu : {name}"}, ensure_ascii=False)


# ---------- Endpoints VAPI ----------

@app.post("/webhook")
async def vapi_webhook(req: Request):
    payload = await req.json()
    message = payload.get("message", {})
    mtype = message.get("type")

    if mtype != "tool-calls":
        # Autres événements (status-update, end-of-call-report, transcript...)
        return {"ok": True}

    call_id = (message.get("call") or {}).get("id")
    tool_calls = message.get("toolCallList") or message.get("toolCalls") or []
    results: list[dict[str, Any]] = []
    for tc in tool_calls:
        fn = tc.get("function") or {}
        name = fn.get("name")
        args = fn.get("arguments", "{}")
        result = dispatch_tool(name, args, call_id=call_id)
        results.append({"toolCallId": tc.get("id"), "result": result})

    return {"results": results}


@app.post("/google-calendar-webhook")
async def gcal_webhook(req: Request):
    # Google envoie des notifications "sync" — on relit les events récents
    sync_recent_changes()
    return {"ok": True}
