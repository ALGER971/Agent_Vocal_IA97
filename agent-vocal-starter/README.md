# 🎙️ agent-vocal-rdv — Agent Vocal IA pour la Prise de RDV

Un agent vocal IA qui répond au téléphone à ta place, comprend le besoin du client et réserve automatiquement un rendez-vous dans ton agenda.

**Flux :** Appel entrant → Agent VAPI (GPT-4o + ElevenLabs) → Google Calendar + Airtable → Dashboard de pilotage

---

## ⚡ Démarrage rapide

### Importer dans VS Code

```bash
git clone https://github.com/mechapizzai-lab/agent-vocal-starter.git
cd agent-vocal-starter
code .
```

### Importer dans Antigravity

```bash
git clone https://github.com/mechapizzai-lab/agent-vocal-starter.git
```

Ouvre ensuite le dossier `agent-vocal-starter` depuis Antigravity.

---

## Concept clé

Plutôt que de manquer des appels ou de passer du temps à qualifier chaque prospect, l'agent vocal prend en charge toute la conversation : il pose les bonnes questions, vérifie tes disponibilités en temps réel et pose le RDV directement dans ton calendrier — sans que tu n'aies à décrocher.

---

## Ce que fait l'agent

- ✅ Répond aux appels entrants 24h/24 en français
- ✅ Pose 2-3 questions pour comprendre le besoin du client
- ✅ Épelle et confirme l'email lettre par lettre pour éviter les erreurs
- ✅ Consulte ton Google Calendar pour proposer des créneaux libres
- ✅ Crée l'événement et envoie l'invitation par email au client
- ✅ Enregistre le contact et le besoin dans Airtable
- ✅ Synchronise les annulations entre Calendar et Airtable

---

## Dashboard de pilotage

Un dashboard web intégré accessible depuis n'importe quel navigateur :

- ✅ Vue de tous les RDV avec statuts (Confirmé / Terminé / Annulé)
- ✅ Stats en temps réel (total, taux de confirmation)
- ✅ Gestion des plages de disponibilité par jour et par horaire
- ✅ Annulation depuis le dashboard → suppression automatique dans Calendar
- ✅ Protégé par mot de passe, persistant entre les sessions

---

## Stack

| Brique | Rôle |
|---|---|
| **VAPI** | Agent vocal + numéro de téléphone |
| **GPT-4o** | Cerveau de la conversation |
| **Deepgram** | Transcription vocale (STT) |
| **ElevenLabs** | Synthèse vocale naturelle (TTS) |
| **Google Calendar** | Disponibilités + réservation |
| **Airtable** | Base de données des RDV |
| **FastAPI** | Serveur webhook |
| **Railway** | Hébergement cloud |

---

## Cas d'usage & monétisation

- Installer l'agent pour ton propre business (coaching, consulting, agence...)
- Proposer le service clé en main à des PME locales (médecins, artisans, coachs)
- Créer une offre d'agence autour de l'agent vocal IA
- Revendre le projet en marque blanche à tes propres clients

---

## Contenu de ce dépôt

```
agent-vocal-starter/
├── Skill.md    # Skill Claude Code utilisé pendant le cours
└── README.md   # Ce fichier
```

Tout le code est construit pas à pas dans le cours vidéo. Ce dépôt est le point de départ.

---

## Membres Skool

Tu es membre payant de la communauté MechaPizzAI ? Tu as accès au **projet complet clé en main** dans la section ressources :

- Code source intégral prêt à déployer
- Version marque blanche pour tes clients
- Dashboard inclus
- Il ne reste qu'à remplir tes clés API

👉 [Rejoindre la communauté MechaPizzAI sur Skool](https://www.skool.com/mechapizzai/about)
