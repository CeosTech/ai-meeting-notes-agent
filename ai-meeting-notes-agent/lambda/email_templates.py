"""Email template helpers for localized meeting summaries."""

from __future__ import annotations

import os
from html import escape
from typing import Dict, Optional, Tuple

_TEMPLATE_OVERRIDES = {
    "subject": "EMAIL_SUBJECT",
    "greeting": "EMAIL_GREETING",
    "intro": "EMAIL_INTRO",
    "summary_heading": "EMAIL_SUMMARY_HEADING",
    "closing": "EMAIL_CLOSING",
    "meta_detected": "EMAIL_META_DETECTED",
    "meta_translated": "EMAIL_META_TRANSLATED",
}

_DEFAULT_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "subject": "Automated Meeting Summary",
        "greeting": "Hello team,",
        "intro": "Here is the automated summary of our meeting.",
        "summary_heading": "Summary",
        "closing": "Regards,\nAI Meeting Notes Agent",
        "meta_detected": "Detected language: {language}",
        "meta_translated": "Translated to: {language}",
    },
    "fr": {
        "subject": "Compte-rendu automatique de la réunion",
        "greeting": "Bonjour à tous,",
        "intro": "Voici le compte-rendu automatique de notre réunion.",
        "summary_heading": "Résumé",
        "closing": "Cordialement,\nAgent AI Meeting Notes",
        "meta_detected": "Langue détectée : {language}",
        "meta_translated": "Résumé traduit en : {language}",
    },
}


def normalize_locale(locale: Optional[str]) -> Optional[str]:
    """Return a normalized locale identifier (lower-case, hyphen-separated)."""

    if not locale:
        return None
    return locale.replace("_", "-").lower()


def _apply_overrides(locale: str, template: Dict[str, str]) -> Dict[str, str]:
    overrides = template.copy()
    suffix = locale.replace("-", "_").upper()
    for key, env_prefix in _TEMPLATE_OVERRIDES.items():
        env_value = os.getenv(f"{env_prefix}_{suffix}")
        if env_value:
            overrides[key] = env_value
    return overrides


def _load_template(locale: str) -> Optional[Dict[str, str]]:
    template = _DEFAULT_TEMPLATES.get(locale)
    if template is None and "-" in locale:
        template = _DEFAULT_TEMPLATES.get(locale.split("-")[0])
    if template is None:
        return None
    return _apply_overrides(locale, template)


def get_email_template(
    preferred_locale: Optional[str],
    default_locale: Optional[str] = "en",
) -> Tuple[str, Dict[str, str]]:
    """Return the resolved locale code and template dictionary."""

    candidates = []
    normalized_preferred = normalize_locale(preferred_locale)
    normalized_default = normalize_locale(default_locale) or "en"

    if normalized_preferred:
        candidates.append(normalized_preferred)
        if "-" in normalized_preferred:
            candidates.append(normalized_preferred.split("-")[0])

    if normalized_default not in candidates:
        candidates.append(normalized_default)
    if "en" not in candidates:
        candidates.append("en")

    for candidate in candidates:
        template = _load_template(candidate)
        if template:
            return candidate, template

    # Fallback
    return "en", _DEFAULT_TEMPLATES["en"].copy()


def render_email_body(
    summary: str,
    template: Dict[str, str],
    detected_language: Optional[str] = None,
    translated_language: Optional[str] = None,
) -> Tuple[str, str]:
    """Render plain-text and HTML bodies for the localized email."""

    def _paragraph(text: str) -> str:
        return f"<p>{escape(text).replace('\n', '<br/>')}</p>"

    meta_lines_text = []
    meta_lines_html = []
    if detected_language:
        line = template.get("meta_detected", "Detected language: {language}").format(
            language=detected_language
        )
        meta_lines_text.append(line)
        meta_lines_html.append(_paragraph(line))
    if translated_language:
        line = template.get("meta_translated", "Translated to: {language}").format(
            language=translated_language
        )
        meta_lines_text.append(line)
        meta_lines_html.append(_paragraph(line))

    text_sections = [
        template.get("greeting", ""),
        template.get("intro", ""),
        "\n".join(meta_lines_text) if meta_lines_text else "",
        f"{template.get('summary_heading', 'Summary')}:",
        summary,
        template.get("closing", ""),
    ]

    body_text = "\n\n".join(section for section in text_sections if section.strip())

    html_sections = [
        "<html><body>",
    ]
    if template.get("greeting"):
        html_sections.append(_paragraph(template["greeting"]))
    if template.get("intro"):
        html_sections.append(_paragraph(template["intro"]))
    html_sections.extend(meta_lines_html)
    html_sections.append(
        f"<h2>{escape(template.get('summary_heading', 'Summary'))}</h2>"
    )
    html_sections.append(
        f"<pre style='font-family: inherit; white-space: pre-wrap;'>{escape(summary)}</pre>"
    )
    if template.get("closing"):
        html_sections.append(_paragraph(template["closing"]))
    html_sections.append("</body></html>")

    body_html = "".join(html_sections)

    return body_text, body_html


def available_locales() -> Dict[str, Dict[str, str]]:
    """Return the base templates without overrides (for documentation/testing)."""

    return _DEFAULT_TEMPLATES.copy()
