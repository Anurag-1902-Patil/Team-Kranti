"""
simulate_whatsapp.py — Simulate WhatsApp Cloud API Webhook calls locally.

Allows testing the WhatsApp ingestion pipeline end-to-end without needing ngrok
or a Meta Developer account. Computes the valid HMAC-SHA256 signature and posts
directly to the FastAPI webhook endpoint.

Usage:
    python scripts/simulate_whatsapp.py --text "Spool erection for Line 24-XX completed today at chainage 12+450"
    python scripts/simulate_whatsapp.py --interactive
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from pathlib import Path
import urllib.request
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1/webhook/whatsapp")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "e6b830d0566502f879aa7247416de708")
PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "1288956324303210")


def send_whatsapp_message(
    text: str,
    sender_phone: str = "919876543210",
    sender_name: str = "Suresh Nair",
    api_url: str = API_URL,
    app_secret: str = APP_SECRET,
):
    msg_id = f"wamid.SIM_{uuid.uuid4().hex[:16]}"
    timestamp = str(int(time.time()))

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": PHONE_ID,
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550234567",
                                "phone_number_id": PHONE_ID,
                            },
                            "contacts": [
                                {
                                    "profile": {"name": sender_name},
                                    "wa_id": sender_phone,
                                }
                            ],
                            "messages": [
                                {
                                    "from": sender_phone,
                                    "id": msg_id,
                                    "timestamp": timestamp,
                                    "text": {"body": text},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    payload_bytes = json.dumps(payload).encode("utf-8")

    # Generate Meta HMAC-SHA256 signature
    sig_hex = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": f"sha256={sig_hex}",
    }

    print(f"\n========================================================")
    print(f" Simulating WhatsApp Incoming Message")
    print(f"========================================================")
    print(f" Sender : {sender_name} ({sender_phone})")
    print(f" Msg ID : {msg_id}")
    print(f" Text   : \"{text}\"")
    print(f" Target : {api_url}")

    req = urllib.request.Request(api_url, data=payload_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.status
            resp_body = resp.read().decode("utf-8")
            print(f"\n [OK] Webhook response ({status_code}): {resp_body}")
            print(f" Celery worker is now extracting, normalizing, and matching in the background.")
            print(f" Check the dashboard at: http://localhost:3000/review or http://localhost:3000")
            return True
    except urllib.error.HTTPError as e:
        print(f"\n [ERROR] Webhook returned HTTP {e.code}: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"\n [ERROR] Could not connect to webhook: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate incoming WhatsApp message.")
    parser.add_argument(
        "--text",
        type=str,
        default="Hydrotesting of 16-inch trunk line section 3 completed today up to 95 bar with zero leakage. Welder team of 6 deployed by ABC Infra at Area B.",
        help="The text content of the message",
    )
    parser.add_argument(
        "--audio",
        type=str,
        default=None,
        help="Path to an audio file (.ogg, .mp3, .wav) to transcribe via faster-whisper and send as voice log",
    )
    parser.add_argument("--sender", type=str, default="919876543210", help="Sender phone number")
    parser.add_argument("--name", type=str, default="Suresh Nair", help="Sender display name")
    parser.add_argument("--interactive", action="store_true", help="Interactive prompt mode")

    args = parser.parse_args()

    if args.audio:
        audio_path = Path(args.audio)
        if not audio_path.exists():
            print(f"[ERROR] Audio file not found: {audio_path}")
            sys.exit(1)
        print(f"\n► Transcribing audio file with faster-whisper: {audio_path.name}...")
        try:
            from backend.services.extraction.asr import transcribe
            audio_bytes = audio_path.read_bytes()
            mime = "audio/ogg" if audio_path.suffix == ".ogg" else "audio/mpeg"
            text_transcribed = transcribe(audio_bytes, mime_type=mime)
            print(f"✓ Transcribed text: \"{text_transcribed}\"")
            send_whatsapp_message(text_transcribed, sender_phone=args.sender, sender_name=args.name)
        except Exception as e:
            print(f"[ERROR] Whisper transcription failed: {e}")
            sys.exit(1)

    elif args.interactive:
        print("--- WhatsApp Simulation Interactive Mode ---")
        while True:
            try:
                user_msg = input("\nEnter update message (or 'exit' to quit): ").strip()
                if not user_msg or user_msg.lower() == "exit":
                    break
                send_whatsapp_message(user_msg, sender_phone=args.sender, sender_name=args.name)
            except (KeyboardInterrupt, EOFError):
                break
    else:
        send_whatsapp_message(args.text, sender_phone=args.sender, sender_name=args.name)

