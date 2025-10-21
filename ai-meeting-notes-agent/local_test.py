import boto3
import json
import os
import sys
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from send_email import send_summary_email

sys.path.append(str(Path(__file__).parent / "lambda"))
from email_templates import get_email_template, render_email_body  # noqa: E402

# Charger les variables d'environnement
load_dotenv()

# Par défaut, on évite d'envoyer des emails pendant les tests locaux.
os.environ.setdefault("SKIP_EMAIL", "1")
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE")
DEFAULT_EMAIL_LOCALE = os.getenv("DEFAULT_EMAIL_LOCALE", "en")
region = os.getenv("AWS_REGION")

if not region:
    raise RuntimeError("AWS_REGION doit être défini dans le fichier .env pour ce test local")

# Client Bedrock
bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
comprehend = boto3.client("comprehend", region_name=region)
translate = boto3.client("translate", region_name=region)

# Charger le transcript local
with open("sample_transcript.txt", "r") as f:
    transcript = f.read()

# Prompt système
system_prompt = """You are a multilingual AI assistant specialized in summarizing meeting transcripts and extracting key action items.
- Detect the language (French or English).
- Respond in the same language.
- Summarize the meeting in no more than 10 bullet points.
- Extract all action items with people or roles.
- Keep a professional tone.
"""

# Messages API format
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"""Here is a transcript:
---
{transcript}
---
Please generate the summary and action items."""
            }
        ]
    }
]

# Requête Bedrock
body = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "system": system_prompt,
    "max_tokens": 1024,
    "temperature": 0.5,
    "messages": messages
})

response = bedrock_runtime.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    contentType="application/json",
    accept="application/json",
    body=body
)

# Résultat JSON
result = json.loads(response["body"].read().decode("utf-8"))

# Nettoyer l'output
clean_text = "\n".join([item["text"].strip() for item in result.get("content", []) if item.get("type") == "text"])

# Afficher dans le terminal
print("\n📄 Résumé généré par l’IA :\n")
print(clean_text)


def detect_language(text: str) -> str | None:
    snippet = text[:4500]
    if not snippet.strip():
        return None
    try:
        response = comprehend.detect_dominant_language(Text=snippet)
        languages = response.get("Languages", [])
        if not languages:
            return None
        languages.sort(key=lambda item: item.get("Score", 0), reverse=True)
        return languages[0].get("LanguageCode")
    except (ClientError, BotoCoreError):
        return None


detected_language = detect_language(transcript)
if detected_language:
    print(f"\n🌐 Langue détectée : {detected_language}")

final_summary = clean_text
translation_applied = False

if TARGET_LANGUAGE and TARGET_LANGUAGE.lower() != (detected_language or "").lower():
    try:
        translation = translate.translate_text(
            Text=clean_text,
            SourceLanguageCode=detected_language or "auto",
            TargetLanguageCode=TARGET_LANGUAGE,
        )
        final_summary = translation.get("TranslatedText", clean_text)
        translation_applied = True
    except (ClientError, BotoCoreError) as error:
        print(f"⚠️ Échec de la traduction ({error})")

if translation_applied:
    print(f"\n🌐 Résumé traduit vers : {TARGET_LANGUAGE}\n")
    print(final_summary)

preferred_email_locale = (
    os.getenv("EMAIL_LOCALE")
    or (TARGET_LANGUAGE if translation_applied else None)
    or detected_language
    or DEFAULT_EMAIL_LOCALE
)
email_locale, email_template = get_email_template(preferred_email_locale, DEFAULT_EMAIL_LOCALE)
body_text, body_html = render_email_body(
    summary=final_summary,
    template=email_template,
    detected_language=detected_language,
    translated_language=TARGET_LANGUAGE if translation_applied else None,
)
print(f"\n✉️ Email locale used: {email_locale}")

result = send_summary_email(
    to_addresses=["participant@example.com"],  # à remplacer par ton email vérifié SES
    subject=email_template.get("subject", "Automated Meeting Summary"),
    body_text=body_text,
    body_html=body_html,
)

if isinstance(result, dict) and result.get("skipped"):
    print("⚠️ Envoi email ignoré (SKIP_EMAIL).")
else:
    print("✅ Email envoyé avec succès")
