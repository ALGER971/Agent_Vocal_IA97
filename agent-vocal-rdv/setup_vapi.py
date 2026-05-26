"""Crée / met à jour l'assistant VAPI. À lancer une fois après avoir rempli WEBHOOK_URL."""
from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

VAPI_KEY = os.getenv("VAPI_PRIVATE_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
COMPANY = os.getenv("COMPANY_NAME", "Notre société")
DESCRIPTION = os.getenv("COMPANY_DESCRIPTION", "")
FIRST_MSG = os.getenv("AGENT_FIRST_MESSAGE", f"Bonjour, bienvenue chez {COMPANY}, comment puis-je vous aider ?")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

if not VAPI_KEY or not WEBHOOK_URL:
    print("❌ VAPI_PRIVATE_KEY et WEBHOOK_URL doivent être définis dans .env")
    sys.exit(1)


SYSTEM_PROMPT = f"""Tu es l'agent vocal de {COMPANY}.
{DESCRIPTION}

OBJECTIF : prendre un rendez-vous pour le client en téléphone.

DÉROULEMENT STRICT :
1. Salue chaleureusement et demande le besoin du client (1-2 phrases).
2. Pose 2 ou 3 questions courtes pour qualifier le besoin.
3. Demande le PRÉNOM et le NOM. Répète le NOM DE FAMILLE lettre par lettre pour validation.
4. Demande l'EMAIL. Épelle-le LETTRE PAR LETTRE pour confirmation. Ne valide qu'après accord explicite du client.
5. Appelle `verifier_disponibilites` avec le nombre de jours souhaité (par défaut 7).
6. Propose UNIQUEMENT les créneaux retournés par l'outil. N'invente jamais de créneaux.
7. Demande confirmation explicite du créneau choisi avant de réserver.
8. Appelle `reserver_creneau` avec start/end ISO du créneau choisi, prenom, nom, email, besoin.
9. Confirme oralement le RDV et précise que l'invitation arrivera par email.
10. Termine poliment.

RÈGLES :
- Parle en français, ton chaleureux et professionnel.
- Phrases courtes. Pas de monologue.
- Si tu ne comprends pas, fais répéter.
- Ne jamais inventer une dispo, un email, ou un horaire.
"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verifier_disponibilites",
            "description": "Récupère les créneaux disponibles dans l'agenda sur les N prochains jours.",
            "parameters": {
                "type": "object",
                "properties": {
                    "jours": {"type": "integer", "description": "Nombre de jours à scanner (défaut 7)."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserver_creneau",
            "description": "Réserve un créneau dans l'agenda et enregistre le contact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "ISO datetime de début"},
                    "end": {"type": "string", "description": "ISO datetime de fin"},
                    "prenom": {"type": "string"},
                    "nom": {"type": "string"},
                    "email": {"type": "string"},
                    "besoin": {"type": "string"},
                },
                "required": ["start", "end", "prenom", "nom", "email", "besoin"],
            },
        },
    },
]


def build_assistant_payload() -> dict:
    return {
        "name": f"Agent RDV - {COMPANY}",
        "firstMessage": FIRST_MSG,
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "tools": TOOLS,
        },
        "voice": {
            "provider": "11labs",
            "voiceId": VOICE_ID,
            "model": "eleven_multilingual_v2",
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "fr",
        },
        "serverUrl": WEBHOOK_URL,
    }


def main():
    headers = {"Authorization": f"Bearer {VAPI_KEY}", "Content-Type": "application/json"}
    payload = build_assistant_payload()
    existing_id = os.getenv("VAPI_ASSISTANT_ID")

    if existing_id:
        r = requests.patch(
            f"https://api.vapi.ai/assistant/{existing_id}",
            headers=headers,
            json=payload,
            timeout=30,
        )
    else:
        r = requests.post(
            "https://api.vapi.ai/assistant",
            headers=headers,
            json=payload,
            timeout=30,
        )

    if not r.ok:
        print(f"❌ Erreur VAPI : {r.status_code}\n{r.text}")
        sys.exit(1)

    data = r.json()
    print(f"✅ Assistant {'mis à jour' if existing_id else 'créé'} : {data.get('id')}")
    print(f"   serverUrl : {WEBHOOK_URL}")
    print("\n👉 Ajoute VAPI_ASSISTANT_ID dans Railway si ce n'est pas déjà fait.")


if __name__ == "__main__":
    main()
