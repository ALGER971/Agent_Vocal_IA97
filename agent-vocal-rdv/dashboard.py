"""Dashboard FastAPI — HTML + API REST protégée par mot de passe."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import airtable_service
import calendar_service

router = APIRouter()

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "changeme")


def _check_auth(authorization: str | None) -> None:
    if not authorization or authorization.replace("Bearer ", "") != DASHBOARD_PASSWORD:
        raise HTTPException(401, "Mot de passe invalide")


# ---------- API ----------

@router.post("/api/login")
async def login(req: Request):
    body = await req.json()
    if body.get("password") != DASHBOARD_PASSWORD:
        raise HTTPException(401, "Mot de passe invalide")
    return {"token": DASHBOARD_PASSWORD}


@router.get("/api/appointments")
def list_appointments(authorization: str | None = Header(None)):
    _check_auth(authorization)
    rows = airtable_service.list_appointments()
    return [{"id": r["id"], **r["fields"]} for r in rows]


class StatusPatch(BaseModel):
    statut: str


@router.patch("/api/appointments/{record_id}/status")
def patch_status(record_id: str, body: StatusPatch, authorization: str | None = Header(None)):
    _check_auth(authorization)
    row = airtable_service._table().get(record_id)
    event_id = row["fields"].get("Calendar Event ID")
    if body.statut == "Annule" and event_id:
        calendar_service.cancel_event(event_id)
    airtable_service.update_status(record_id, body.statut)
    return {"ok": True}


@router.get("/api/availability")
def get_availability(authorization: str | None = Header(None)):
    _check_auth(authorization)
    return airtable_service.get_availability_ranges()


@router.post("/api/availability")
async def post_availability(req: Request, authorization: str | None = Header(None)):
    _check_auth(authorization)
    ranges = await req.json()
    airtable_service.save_availability_ranges(ranges)
    return {"ok": True}


# ---------- HTML ----------

DASHBOARD_HTML = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dashboard — Agent Vocal RDV</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 20px 32px; background: #1e293b; display: flex; justify-content: space-between; align-items: center; }
    header h1 { margin: 0; font-size: 20px; }
    main { padding: 32px; max-width: 1200px; margin: 0 auto; }
    .tabs { display: flex; gap: 8px; margin-bottom: 24px; }
    .tab { padding: 10px 16px; background: #1e293b; border-radius: 8px; cursor: pointer; }
    .tab.active { background: #3b82f6; }
    .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .card { background: #1e293b; padding: 20px; border-radius: 12px; }
    .card .v { font-size: 28px; font-weight: 700; }
    .card .l { font-size: 12px; opacity: 0.7; text-transform: uppercase; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #334155; font-size: 14px; }
    th { background: #334155; font-weight: 600; }
    .badge { padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
    .b-Confirme { background: #1e3a8a; color: #93c5fd; }
    .b-Termine { background: #14532d; color: #86efac; }
    .b-Annule { background: #7f1d1d; color: #fca5a5; }
    select, input, button { background: #0f172a; color: #e2e8f0; border: 1px solid #334155; padding: 8px 12px; border-radius: 8px; font-size: 14px; }
    button { cursor: pointer; background: #3b82f6; border-color: #3b82f6; }
    button.danger { background: #dc2626; border-color: #dc2626; }
    .login { max-width: 360px; margin: 80px auto; background: #1e293b; padding: 32px; border-radius: 12px; }
    .login input { width: 100%; margin: 12px 0; }
    .login button { width: 100%; }
    .row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
    .row label { width: 100px; font-size: 13px; }
    .hidden { display: none; }
  </style>
</head>
<body>
  <div id="login" class="login">
    <h2>Connexion</h2>
    <input id="pwd" type="password" placeholder="Mot de passe" />
    <button onclick="login()">Entrer</button>
    <div id="err" style="color:#fca5a5;font-size:13px;margin-top:8px;"></div>
  </div>

  <div id="app" class="hidden">
    <header>
      <h1>📞 Agent Vocal RDV</h1>
      <button onclick="logout()" class="danger">Déconnexion</button>
    </header>
    <main>
      <div class="tabs">
        <div class="tab active" data-tab="rdv" onclick="switchTab('rdv')">Rendez-vous</div>
        <div class="tab" data-tab="dispo" onclick="switchTab('dispo')">Disponibilités</div>
      </div>

      <section id="tab-rdv">
        <div class="stats">
          <div class="card"><div class="v" id="s-total">0</div><div class="l">Total</div></div>
          <div class="card"><div class="v" id="s-conf">0</div><div class="l">Confirmés</div></div>
          <div class="card"><div class="v" id="s-term">0</div><div class="l">Terminés</div></div>
          <div class="card"><div class="v" id="s-rate">0%</div><div class="l">Taux confirmation</div></div>
        </div>
        <div style="margin-bottom:12px;">
          <select id="filter" onchange="render()">
            <option value="">Tous statuts</option>
            <option>Confirme</option>
            <option>Termine</option>
            <option>Annule</option>
          </select>
        </div>
        <table>
          <thead><tr><th>Date</th><th>Client</th><th>Email</th><th>Besoin</th><th>Statut</th><th>Actions</th></tr></thead>
          <tbody id="rows"></tbody>
        </table>
      </section>

      <section id="tab-dispo" class="hidden">
        <h2>Plages de disponibilité</h2>
        <div id="ranges"></div>
        <button onclick="addRange()">+ Ajouter une plage</button>
        <button onclick="saveRanges()" style="margin-left:8px;">💾 Sauvegarder</button>
      </section>
    </main>
  </div>

<script>
const JOURS = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"];
let TOKEN = localStorage.getItem("dash_token") || "";
let APPTS = [];
let RANGES = [];

function authHeaders() { return { "Authorization": "Bearer " + TOKEN, "Content-Type": "application/json" }; }

async function login() {
  const pwd = document.getElementById("pwd").value;
  const r = await fetch("/api/login", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({password: pwd}) });
  if (!r.ok) { document.getElementById("err").textContent = "Mot de passe invalide"; return; }
  const d = await r.json();
  TOKEN = d.token; localStorage.setItem("dash_token", TOKEN);
  showApp();
}
function logout() { localStorage.removeItem("dash_token"); TOKEN = ""; location.reload(); }

async function showApp() {
  document.getElementById("login").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  await loadAppointments();
  await loadRanges();
}

async function loadAppointments() {
  const r = await fetch("/api/appointments", { headers: authHeaders() });
  if (r.status === 401) { logout(); return; }
  APPTS = await r.json();
  render();
}

function render() {
  const filter = document.getElementById("filter").value;
  const list = filter ? APPTS.filter(a => a.Statut === filter) : APPTS;
  const total = APPTS.length;
  const conf = APPTS.filter(a => a.Statut === "Confirme").length;
  const term = APPTS.filter(a => a.Statut === "Termine").length;
  document.getElementById("s-total").textContent = total;
  document.getElementById("s-conf").textContent = conf;
  document.getElementById("s-term").textContent = term;
  document.getElementById("s-rate").textContent = total ? Math.round((conf+term)/total*100) + "%" : "0%";

  document.getElementById("rows").innerHTML = list.map(a => `
    <tr>
      <td>${a["Date RDV"] || ""}</td>
      <td>${a.Prenom || ""} ${a.Nom || ""}</td>
      <td>${a.Email || ""}</td>
      <td>${(a.Besoin || "").slice(0,60)}</td>
      <td><span class="badge b-${a.Statut}">${a.Statut || ""}</span></td>
      <td>
        <select onchange="setStatus('${a.id}', this.value)">
          <option>—</option>
          <option>Confirme</option>
          <option>Termine</option>
          <option>Annule</option>
        </select>
      </td>
    </tr>`).join("");
}

async function setStatus(id, statut) {
  if (statut === "—") return;
  await fetch(`/api/appointments/${id}/status`, { method: "PATCH", headers: authHeaders(), body: JSON.stringify({statut}) });
  await loadAppointments();
}

async function loadRanges() {
  const r = await fetch("/api/availability", { headers: authHeaders() });
  RANGES = await r.json();
  renderRanges();
}

function renderRanges() {
  document.getElementById("ranges").innerHTML = RANGES.map((rg, i) => `
    <div class="card" style="margin-bottom:12px;">
      <div class="row"><label>Libellé</label><input value="${rg.label||""}" oninput="RANGES[${i}].label=this.value" /></div>
      <div class="row"><label>Jours</label>${JOURS.map((j,k)=>`<label style="width:auto;"><input type="checkbox" ${(rg.jours||[]).includes(k)?"checked":""} onchange="toggleDay(${i},${k},this.checked)" /> ${j}</label>`).join("")}</div>
      <div class="row"><label>Début</label><input type="number" min="0" max="23" value="${rg.debut||9}" oninput="RANGES[${i}].debut=parseInt(this.value)" /></div>
      <div class="row"><label>Fin</label><input type="number" min="0" max="23" value="${rg.fin||17}" oninput="RANGES[${i}].fin=parseInt(this.value)" /></div>
      <button class="danger" onclick="removeRange(${i})">Supprimer</button>
    </div>`).join("");
}
function toggleDay(i, k, on) {
  const arr = new Set(RANGES[i].jours || []);
  on ? arr.add(k) : arr.delete(k);
  RANGES[i].jours = [...arr].sort();
}
function addRange() { RANGES.push({id: String(Date.now()), label: "Nouvelle plage", jours: [0,1,2,3,4], debut: 9, fin: 17}); renderRanges(); }
function removeRange(i) { RANGES.splice(i,1); renderRanges(); }
async function saveRanges() {
  await fetch("/api/availability", { method: "POST", headers: authHeaders(), body: JSON.stringify(RANGES) });
  alert("Sauvegardé");
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  document.getElementById("tab-rdv").classList.toggle("hidden", name !== "rdv");
  document.getElementById("tab-dispo").classList.toggle("hidden", name !== "dispo");
}

if (TOKEN) showApp();
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML
