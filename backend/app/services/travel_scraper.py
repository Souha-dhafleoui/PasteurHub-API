from __future__ import annotations

from typing import Dict, List, Optional
import re
import requests
from bs4 import BeautifulSoup

PASTEUR_FR_COUNTRY_INDEX_URL = "https://www.pasteur.fr/fr/data/export/json/fiche_pays/fr"
PASTEUR_FR_BASE_URL = "https://www.pasteur.fr/fr/"

# We only care about travel-vaccine headings that we can map to Tunisia (IPT) vaccines.
# The page may contain other vaccines; we ignore those for pricing.
FR_VACCINE_ALIASES: Dict[str, List[str]] = {
    "yellow_fever": ["Fièvre jaune"],
    "hepatitis_a": ["Hépatite A"],
    "hepatitis_b": ["Hépatite B"],
    "typhoid": ["Typhoïde"],
    "rabies": ["Rage"],
    "polio": ["Poliomyélite"],
    "meningitis": ["Méningite", "Méningite A", "Méningite ACYW", "Méningite A/C/Y/W135", "Méningocoque"],
    "dt": ["Diphtérie", "Tétanos", "Diphtérie - Tétanos", "Diphtérie-tétanos"],
    "mmr": ["Rougeole", "Oreillons", "Rubéole", "Rougeole, oreillons, rubéole"],
    "pneumo": ["Pneumocoque", "Pneumococcique"],
}

STOP_MARKERS = {
    "Paludisme",
    "Sources",
    "/// AVERTISSEMENT",
    "AVERTISSEMENT",
    "Dernière mise à jour",
}


def _norm(s: str) -> str:
    return " ".join((s or "").strip().split())


def fetch_country_index(timeout: int = 30) -> List[dict]:
    """
    Returns list of:
      { "name": <country label from Pasteur.fr>, "url": <full url>, "path": <path> }
    """
    r = requests.get(
        PASTEUR_FR_COUNTRY_INDEX_URL,
        timeout=timeout,
        headers={"User-Agent": "pasteurhub/1.0"},
    )
    r.raise_for_status()
    payload = r.json()
    data = payload.get("data", []) or []

    out: List[dict] = []
    for item in data:
        name = _norm(item.get("value", ""))
        path = item.get("path", "") or ""
        if not name or not path:
            continue

        # In JSON, slashes may appear escaped if you print raw; fix just in case.
        path = path.replace("\\/", "/").lstrip("/")
        url = PASTEUR_FR_BASE_URL + path
        out.append({"name": name, "url": url, "path": path})

    return out


def _match_heading_to_key(line: str) -> Optional[str]:
    """
    Returns our internal key if line looks like a vaccine heading in French.
    """
    l = _norm(line)
    if not l:
        return None

    # Remove common heading punctuation like ":".
    l = l.rstrip(":").strip()

    for key, aliases in FR_VACCINE_ALIASES.items():
        for a in aliases:
            # exact match or startswith, to catch things like "Méningite A/C/Y/W135"
            if l == a or l.startswith(a):
                return key
    return None


def scrape_country_recommendations(country_url: str, timeout: int = 30) -> dict:
    """
    Scrape Pasteur.fr country page and extract recommended vaccine sections.

    Returns:
      {
        "source_url": country_url,
        "last_updated": "<string or None>",
        "items": [
            {"key": "hepatitis_a", "label_fr": "Hépatite A", "requirement_level": "recommended", "notes_fr": "..."},
            ...
        ]
      }
    """
    r = requests.get(country_url, timeout=timeout, headers={"User-Agent": "pasteurhub/1.0"})
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    lines = [_norm(x) for x in soup.get_text("\n").splitlines()]
    lines = [x for x in lines if x]

    # Find update date (if present)
    last_updated = None
    for line in reversed(lines):
        m = re.search(r"Dernière mise à jour le\s+(.+)$", line, flags=re.I)
        if m:
            last_updated = _norm(m.group(1))
            break

    # Find "Vaccinations recommandées"
    start_idx = None
    for i, line in enumerate(lines):
        if "Vaccinations recommandées" in line:
            start_idx = i
            break

    if start_idx is None:
        return {"source_url": country_url, "last_updated": last_updated, "items": []}

    # Build the block after that until a stop marker
    block: List[str] = []
    for line in lines[start_idx + 1 :]:
        if any(line.startswith(m) or line == m for m in STOP_MARKERS):
            break
        block.append(line)

    items: List[dict] = []
    idx = 0
    while idx < len(block):
        key = _match_heading_to_key(block[idx])
        if not key:
            idx += 1
            continue

        label_fr = block[idx].rstrip(":").strip()
        idx += 1
        notes_lines: List[str] = []

        while idx < len(block):
            # stop if next heading or stop marker-like section
            if _match_heading_to_key(block[idx]):
                break
            if any(block[idx].startswith(m) or block[idx] == m for m in STOP_MARKERS):
                break
            notes_lines.append(block[idx])
            idx += 1

        notes_fr = _norm(" ".join(notes_lines))

        requirement_level = "recommended"
        # If the note mentions "exigé/exigée/obligatoire/requis", treat as required.
        if re.search(r"\bexig[ée]\b|\bobligatoire\b|\brequis\b", notes_fr, flags=re.I):
            requirement_level = "required"

        items.append(
            {
                "key": key,
                "label_fr": label_fr,
                "requirement_level": requirement_level,
                "notes_fr": notes_fr,
            }
        )

    return {"source_url": country_url, "last_updated": last_updated, "items": items}
