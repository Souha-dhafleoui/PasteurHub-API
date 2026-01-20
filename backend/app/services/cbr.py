from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.vaccine import Vaccine

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


KEYWORDS = {
    "fever": ["fever", "chills", "mosquito", "headache", "tropical"],
    "gastro": ["diarrhea", "vomit", "vomiting", "cramps", "stomach", "food", "street food"],
    "food_water": ["water", "unsafe water", "food/water", "hepatitis a", "unsafe meals", "contaminated"],
    "bite": ["bite", "scratch", "dog", "cat", "rabies", "animal"],
    "wound": ["wound", "cut", "rusty", "nail", "puncture", "tetanus", "dirty metal"],
    "crowd": ["crowd", "pilgrimage", "mass gathering", "dorm", "festival", "meningitis"],
    "risk": ["sex", "blood", "needle", "healthcare", "exposure", "hepatitis b"],
    "polio": ["polio", "booster", "circulation", "long stay"],
    "childhood": ["child", "school", "mmr", "measles", "mumps", "rubella"],
    "respiratory": ["pneumonia", "pneumococcal", "lung", "respiratory", "elderly"],
}

# Users type free-form scenario values like "dog bite" or "mosquito fever".
# We normalize those to our internal Case.scenario_type codes.
SCENARIO_MAP = {
    # bite
    "dog bite": "bite",
    "cat bite": "bite",
    "animal bite": "bite",
    "dog scratch": "bite",
    "cat scratch": "bite",
    "rabies": "bite",
    "bite": "bite",
    # fever
    "mosquito fever": "fever",
    "yellow fever": "fever",
    "tropical fever": "fever",
    "fever": "fever",
    "chills": "fever",
    # gastro
    "food poisoning": "gastro",
    "diarrhea": "gastro",
    "vomiting": "gastro",
    "stomach": "gastro",
    "gastro": "gastro",
    # food/water
    "unsafe water": "food_water",
    "food/water": "food_water",
    "hepatitis a": "food_water",
    # wound
    "rusty nail": "wound",
    "tetanus": "wound",
    "wound": "wound",
    "cut": "wound",
    # risk
    "needle": "risk",
    "needle stick": "risk",
    "blood exposure": "risk",
    "healthcare exposure": "risk",
    "sexual exposure": "risk",
    "risk": "risk",
    "hepatitis b": "risk",
    # crowd
    "pilgrimage": "crowd",
    "mass gathering": "crowd",
    "dorm": "crowd",
    "festival": "crowd",
    "crowd": "crowd",
    "meningitis": "crowd",
    # polio
    "polio booster": "polio",
    "polio": "polio",
    # childhood
    "child": "childhood",
    "mmr": "childhood",
    "measles": "childhood",
    "school": "childhood",
    # respiratory
    "pneumonia": "respiratory",
    "pneumococcal": "respiratory",
    "respiratory": "respiratory",
    "lung": "respiratory",
}


def normalize_scenario(user_value: Optional[str]) -> str:
    """
    Map user input to internal scenario codes.
    Returns "" if not recognized (so we can infer from text).
    """
    if not user_value:
        return ""
    s = user_value.strip().lower()
    if not s:
        return ""
    if s in SCENARIO_MAP:
        return SCENARIO_MAP[s]
    # phrase containment (e.g., "I had a dog bite" -> bite)
    for phrase, code in SCENARIO_MAP.items():
        if phrase in s:
            return code
    return ""


def infer_scenario(text: str) -> Optional[str]:
    t = (text or "").lower()
    best = None
    best_score = 0
    for scen, words in KEYWORDS.items():
        score = sum(1 for w in words if w in t)
        if score > best_score:
            best_score = score
            best = scen
    return best if best_score >= 1 else None


def find_similar_cases(
    db: Session,
    query_text: str,
    scenario_type: Optional[str],
    top_k: int,
) -> List[dict]:
    """
    Find similar cases based on text and scenario matching.
    No age filtering - simplified version.
    """
    rows = (
        db.query(Case, Vaccine)
        .join(Vaccine, Vaccine.id == Case.vaccine_id)
        .all()
    )
    if not rows:
        return []

    # Normalize and infer scenario
    q_scenario = normalize_scenario(scenario_type)
    if not q_scenario:
        q_scenario = infer_scenario(query_text) or ""

    # Scenario-first filtering (critical for "dog bite" -> bite/rabies)
    scenario_rows = rows
    if q_scenario:
        scenario_rows = [(c, v) for (c, v) in rows if (c.scenario_type or "").strip().lower() == q_scenario]
        if not scenario_rows:
            scenario_rows = rows  # fallback if DB has no such scenario

    filtered = scenario_rows

    cases = [c for (c, _) in filtered]
    vaccines = [v for (_, v) in filtered]
    corpus = [c.problem_text for c in cases]

    # Semantic similarity (TF-IDF word + char)
    word_vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))

    word_mat = word_vec.fit_transform(corpus + [query_text])
    char_mat = char_vec.fit_transform(corpus + [query_text])

    word_sims = cosine_similarity(word_mat[-1], word_mat[:-1]).flatten()
    char_sims = cosine_similarity(char_mat[-1], char_mat[:-1]).flatten()
    semantic = 0.75 * word_sims + 0.25 * char_sims

    # Context scoring: scenario match only
    scenario_scores = []
    for c in cases:
        c_s = (c.scenario_type or "").strip().lower()
        if not q_scenario:
            scen_score = 0.5
        else:
            scen_score = 1.0 if c_s == q_scenario else 0.0
        scenario_scores.append(scen_score)

    scenario_arr = np.array(scenario_scores, dtype=float)
    context = scenario_arr

    # Final score: 75% semantic, 25% context
    final = 0.75 * semantic + 0.25 * context

    ranked = final.argsort()[::-1]
    top_k = max(1, top_k)
    take = ranked[: min(top_k, len(ranked))]

    results: List[dict] = []
    for i in take:
        i = int(i)
        c = cases[i]
        v = vaccines[i]
        results.append(
            {
                "case_id": c.id,
                "score": float(final[i]),
                "problem_text": c.problem_text,
                "scenario_type": c.scenario_type,
                "vaccine_id": c.vaccine_id,
                "vaccine_name": v.name,
                "vaccine_description": v.description,
                "semantic_score": float(semantic[i]),
                "context_score": float(context[i]),
                "scenario_match": bool(scenario_arr[i] == 1.0),
            }
        )

    # Guarantee at least 1 if DB had cases
    if not results and cases:
        c = cases[0]
        v = vaccines[0]
        results.append(
            {
                "case_id": c.id,
                "score": 0.0,
                "problem_text": c.problem_text,
                "scenario_type": c.scenario_type,
                "vaccine_id": c.vaccine_id,
                "vaccine_name": v.name,
                "vaccine_description": v.description,
                "semantic_score": 0.0,
                "context_score": 0.0,
                "scenario_match": False,
            }
        )

    return results