# 🎙️ agent-vocal-rdv

Agent vocal IA pour la prise de RDV — VAPI + GPT-4o + Google Calendar + Airtable, hébergé sur Railway.

## Installation locale

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # puis remplis tes clés
```

## Setup pas à pas

1. **Google Cloud** : créer projet → activer Calendar API → OAuth 2.0 (Desktop) → télécharger `credentials.json` à la racine.
2. **Premier OAuth local** : `python -c "import calendar_service; calendar_service.get_credentials()"` → ouvre le navigateur → génère `token.json`.
3. **Airtable** : créer une base, récupérer `AIRTABLE_BASE_ID`, créer un PAT (`schema.bases:read/write`, `data.records:read/write`).
4. `python setup_airtable.py` → crée les tables.
5. `python launch.py --ngrok` → tunnel + serveur local, copie l'URL ngrok dans `.env` (WEBHOOK_URL).
6. `python setup_vapi.py` → crée l'assistant VAPI, copie l'ID retourné dans `.env`.
7. Dashboard local : http://localhost:8000/dashboard (mdp = `DASHBOARD_PASSWORD`).

## Déploiement Railway

```bash
python encode_token.py  # affiche GOOGLE_TOKEN_JSON + GOOGLE_CREDENTIALS_JSON
```

1. Pousser le code sur GitHub.
2. Railway → New Project → Deploy from GitHub.
3. Ajouter TOUTES les variables de `.env.example`.
4. Récupérer l'URL Railway → mettre `WEBHOOK_URL=https://xxx.up.railway.app/webhook`.
5. Relancer `python setup_vapi.py` en local avec la nouvelle WEBHOOK_URL pour mettre à jour l'assistant.

## Endpoints

| Route | Description |
|---|---|
| `GET /` | Health check |
| `GET /debug/calendar` | Vérifie la connexion Google Calendar |
| `POST /webhook` | Tool-calls VAPI |
| `POST /google-calendar-webhook` | Notifications Calendar → sync Airtable |
| `GET /dashboard` | Dashboard web |

## Structure

```
agent-vocal-rdv/
├── main.py                  # Webhook FastAPI
├── calendar_service.py      # Google Calendar
├── airtable_service.py      # Airtable
├── calendar_watch.py        # Sync annulations
├── dashboard.py             # Dashboard web
├── setup_vapi.py            # Création assistant VAPI
├── setup_airtable.py        # Création tables Airtable
├── encode_token.py          # Token Google → base64
├── launch.py                # Démarrage local
├── Procfile                 # Railway
├── requirements.txt
└── .env.example
```
