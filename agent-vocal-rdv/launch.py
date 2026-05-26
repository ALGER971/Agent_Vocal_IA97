"""Démarrage local — uvicorn + tunnel ngrok optionnel."""
from __future__ import annotations

import os
import subprocess
import sys
import time

from dotenv import load_dotenv

load_dotenv(override=True)


def start_ngrok(port: int) -> str | None:
    if "--ngrok" not in sys.argv:
        return None

    # Essai avec ngrok CLI système (brew install ngrok)
    try:
        subprocess.Popen(
            ["ngrok", "http", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        # Récupère l'URL via l'API locale ngrok
        import urllib.request, json
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as r:
            data = json.loads(r.read())
        for t in data.get("tunnels", []):
            if t.get("proto") == "https":
                url = t["public_url"]
                print(f"🌐 Ngrok : {url}")
                print(f"   Webhook : {url}/webhook")
                os.environ["WEBHOOK_URL"] = f"{url}/webhook"
                return url
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[ngrok] erreur API locale : {e}")

    # Fallback : pyngrok
    try:
        import ssl, certifi
        ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
        from pyngrok import ngrok
        tunnel = ngrok.connect(port, "http")
        url = tunnel.public_url
        print(f"🌐 Ngrok : {url}")
        print(f"   Webhook : {url}/webhook")
        os.environ["WEBHOOK_URL"] = f"{url}/webhook"
        return url
    except Exception as e:
        print(f"[pyngrok] erreur : {e}")
        print("💡 Installe ngrok : brew install ngrok/ngrok/ngrok")
        print("   Ou corrige SSL : /Applications/Python\\ 3.13/Install\\ Certificates.command")
        return None


def main():
    port = int(os.getenv("PORT", "8000"))
    start_ngrok(port)
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
