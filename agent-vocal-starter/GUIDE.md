# 📖 Guide complet — Construire l'Agent Vocal RDV depuis zéro

Ce guide accompagne le cours vidéo MechaPizzAI. Il récapitule toutes les étapes pour arriver à une version fonctionnelle et déployée de l'agent vocal.

---

## Vue d'ensemble de ce que tu vas construire

```
┌─────────────────────────────────────────────────────────┐
│                     ARCHITECTURE                        │
│                                                         │
│  Appelant ──► Numéro VAPI                               │
│                    │                                    │
│              Agent VAPI                                 │
│         (GPT-4o + ElevenLabs + Deepgram)                │
│                    │                                    │
│         Webhook FastAPI (Railway)                       │
│              │           │                              │
│    Google Calendar    Airtable                          │
│    (créneaux + RDV)   (contacts)                        │
│                    │                                    │
│            Dashboard /dashboard                         │
└─────────────────────────────────────────────────────────┘
```

---

## Étape 0 — Créer tous les comptes

Avant d'écrire la moindre ligne de code, tu dois avoir accès à ces services :

| Service | URL | Gratuit ? | Pourquoi |
|---|---|---|---|
| VAPI | vapi.ai | Oui (trial) | Agent vocal + numéro |
| OpenAI | platform.openai.com | Non (pay-as-you-go) | GPT-4o |
| ElevenLabs | elevenlabs.io | Oui (limité) | Voix réaliste |
| Google Cloud | console.cloud.google.com | Oui | Calendar API |
| Airtable | airtable.com | Oui | Base de données |
| Railway | railway.app | Oui (5$/mois après trial) | Hébergement |

---

## Étape 1 — Structure du projet

Crée un dossier `agent-vocal-rdv/` et initialise-le :

```bash
mkdir agent-vocal-rdv
cd agent-vocal-rdv
pip install fastapi uvicorn python-dotenv google-auth google-auth-oauthlib google-api-python-client pyairtable pytz requests pyngrok
```

Structure finale que tu vas construire :

```
agent-vocal-rdv/
├── main.py                  # Serveur webhook FastAPI
├── calendar_service.py      # Google Calendar
├── airtable_service.py      # Airtable
├── calendar_watch.py        # Sync annulations Calendar → Airtable
├── dashboard.py             # Dashboard web
├── setup_vapi.py            # Création assistant VAPI (à lancer une fois)
├── setup_airtable.py        # Création tables Airtable (à lancer une fois)
├── encode_token.py          # Encode le token Google pour Railway
├── launch.py                # Démarrage local
├── Procfile                 # Railway
├── requirements.txt
└── .env
```

---

## Étape 2 — Le serveur webhook (main.py)

Le serveur reçoit les appels d'outils de VAPI via HTTP POST sur `/webhook`.

**Ce que tu dois implémenter :**
- Endpoint `POST /webhook` qui lit les `tool-calls` VAPI
- Fonction `dispatch_tool` qui route vers le bon service
- Endpoint `POST /google-calendar-webhook` pour les notifications Calendar
- Démarrage automatique du watch Calendar au lancement du serveur

**Format des tool-calls VAPI :**
```json
{
  "message": {
    "type": "tool-calls",
    "toolCallList": [{
      "id": "tc-xxx",
      "function": {
        "name": "verifier_disponibilites",
        "arguments": "{\"jours\": 7}"
      }
    }]
  }
}
```

**Format de réponse attendu par VAPI :**
```json
{
  "results": [{
    "toolCallId": "tc-xxx",
    "result": "Créneaux disponibles : ..."
  }]
}
```

---

## Étape 3 — Google Calendar (calendar_service.py)

**Ce que tu dois implémenter :**
- Authentification OAuth 2.0 avec sauvegarde du token
- Restauration du token depuis une variable d'env en production
- `get_available_slots(days_ahead)` → vérifie freebusy + plages de dispo
- `format_slots_for_agent(slots)` → format lisible + format machine pour VAPI
- `book_appointment(...)` → crée l'événement + envoie invitation email
- `cancel_event(event_id)` → supprime l'événement

**Configuration Google Cloud :**
1. Créer un projet → activer Calendar API
2. Créer des credentials OAuth 2.0 (Desktop app)
3. Télécharger `credentials.json`
4. Lancer le flow OAuth local → génère `token.json`

---

## Étape 4 — Airtable (airtable_service.py)

**Table `Rendez-vous` — champs requis :**

| Champ | Type |
|---|---|
| Prenom | Single line text |
| Nom | Single line text |
| Email | Email |
| Date RDV | Single line text |
| Besoin | Long text |
| Statut | Single select (Confirme / Annule / Termine) |
| Cree le | Single line text |
| Call ID | Single line text |
| Calendar Event ID | Single line text |

**Table `Config` — champs requis :**

| Champ | Type |
|---|---|
| Cle | Single line text |
| Valeur | Long text |

La table Config stocke les plages de disponibilité au format JSON :
```json
[{"id": "1", "label": "Semaine", "jours": [0,1,2,3,4], "debut": 9, "fin": 17}]
```

**Token Airtable requis :**
- Scopes : `schema.bases:read`, `schema.bases:write`, `data.records:write`, `data.records:read`

---

## Étape 5 — L'assistant VAPI (setup_vapi.py)

**Ce que tu dois configurer dans l'assistant :**

```python
{
  "model": {
    "provider": "openai",
    "model": "gpt-4o",
    "tools": [
      {"name": "verifier_disponibilites", ...},
      {"name": "reserver_creneau", ...}
    ]
  },
  "voice": {
    "provider": "11labs",
    "voiceId": "ton-voice-id",
    "model": "eleven_multilingual_v2"
  },
  "transcriber": {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "fr"
  },
  "serverUrl": "https://ton-app.railway.app/webhook"
}
```

**System prompt — points clés à inclure :**
- Procédure stricte de confirmation email (épeler lettre par lettre)
- Répétition du nom de famille pour validation
- Utiliser uniquement les créneaux retournés par `verifier_disponibilites`
- Demander confirmation avant d'appeler `reserver_creneau`

---

## Étape 6 — Le dashboard (dashboard.py)

Un router FastAPI qui sert une page HTML protégée par mot de passe.

**Routes à implémenter :**
- `GET /dashboard` → page HTML complète
- `GET /api/appointments` → liste des RDV depuis Airtable
- `PATCH /api/appointments/{id}/status` → change statut + annule Calendar si besoin
- `GET /api/availability` → plages de dispo depuis Airtable Config
- `POST /api/availability` → sauvegarde les plages

**Fonctionnalités du dashboard :**
- Authentification par mot de passe (`DASHBOARD_PASSWORD` en env)
- Persistance du token via `localStorage`
- Stats (total, confirmés, terminés, taux)
- Filtres par statut
- Onglet Disponibilités avec plages paramétrables

---

## Étape 7 — Déploiement Railway

**Procfile :**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Variables d'environnement Railway :**
```
COMPANY_NAME
COMPANY_DESCRIPTION
AGENT_FIRST_MESSAGE
VAPI_PRIVATE_KEY
VAPI_PUBLIC_KEY
VAPI_ASSISTANT_ID
OPENAI_API_KEY
ELEVENLABS_API_KEY
AIRTABLE_API_KEY
AIRTABLE_BASE_ID
AIRTABLE_TABLE_NAME
GOOGLE_CALENDAR_ID
GOOGLE_TOKEN_JSON       ← obtenu via encode_token.py
GOOGLE_CREDENTIALS_JSON ← credentials.json encodé en base64
WEBHOOK_URL             ← URL Railway + /webhook
DASHBOARD_PASSWORD
```

**Ordre des opérations :**
1. Pousser le code sur GitHub
2. Connecter Railway au repo GitHub
3. Ajouter toutes les variables
4. Récupérer l'URL Railway
5. Ajouter `WEBHOOK_URL` dans Railway
6. Lancer `python setup_vapi.py` en local avec `WEBHOOK_URL` rempli
7. Ajouter `VAPI_ASSISTANT_ID` dans Railway

---

## Étape 8 — Numéro de téléphone VAPI

1. Dashboard VAPI → Phone Numbers → Create Phone Number
2. Choisir "Free Vapi Number" → entrer un area code US (ex: `415`)
3. Assigner l'assistant "Agent RDV - Ta Société"
4. Tester en appelant le numéro

---

## Étape 9 — Tests de validation

| Test | Résultat attendu |
|---|---|
| `GET /` | `{"status": "Agent Vocal RDV actif"}` |
| `GET /debug/calendar` | `{"ok": true, "slots": N}` |
| Appel téléphonique | Agent répond en français |
| Donner un email | Agent épelle et confirme |
| Valider un créneau | RDV dans Calendar + ligne dans Airtable |
| Annuler dans dashboard | Event supprimé dans Calendar |
| Annuler dans Calendar | Statut "Annule" dans Airtable |

---

## Ressources

- Documentation VAPI : docs.vapi.ai
- Google Calendar API : developers.google.com/calendar
- pyairtable : pyairtable.readthedocs.io
- FastAPI : fastapi.tiangolo.com

👉 [Rejoindre la communauté MechaPizzAI sur Skool](https://www.skool.com/mechapizzai/about)
