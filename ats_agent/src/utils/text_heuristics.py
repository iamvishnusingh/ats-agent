"""Rule-based resume sectioning, keywords, and skill hints for LangGraph tools."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from fuzzywuzzy import fuzz

_STOP: set | None = None


def _stopwords() -> set:
    global _STOP
    if _STOP is None:
        try:
            from nltk.corpus import stopwords

            _STOP = set(stopwords.words("english"))
        except Exception:
            _STOP = set()
    return _STOP


def _tokens(text: str) -> List[str]:
    try:
        from nltk.tokenize import word_tokenize

        raw = word_tokenize(text.lower())
    except Exception:
        raw = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", text.lower())
    stop = _stopwords()
    out: List[str] = []
    for w in raw:
        if len(w) < 3 or w in stop:
            continue
        if w.isalpha() or w.replace(".", "").isalnum():
            out.append(w)
    return out


class ResumeTextHeuristics:
    """Lightweight helpers for tool nodes (sections, keywords, fuzzy match, skills)."""

    _SECTION_ALIASES = (
        ("summary", re.compile(r"^(profile|summary|objective)\s*:?\s*$", re.I)),
        ("experience", re.compile(r"^(experience|employment|work history)\s*:?\s*$", re.I)),
        ("education", re.compile(r"^education\s*:?\s*$", re.I)),
        ("skills", re.compile(r"^(skills|technical skills)\s*:?\s*$", re.I)),
        ("projects", re.compile(r"^projects\s*:?\s*$", re.I)),
    )

    def analyze_resume_sections(self, text: str) -> Dict[str, str]:
        lines = text.splitlines()
        sections: Dict[str, List[str]] = {k: [] for k, _ in self._SECTION_ALIASES}
        sections["other"] = []
        current = "other"
        for line in lines:
            stripped = line.strip()
            matched = False
            for name, pat in self._SECTION_ALIASES:
                if pat.match(stripped):
                    current = name
                    matched = True
                    break
            if not matched:
                sections[current].append(line)
        return {k: "\n".join(v).strip() for k, v in sections.items()}

    def extract_keywords(self, text: str) -> List[str]:
        toks = _tokens(text)
        freq: Dict[str, int] = {}
        for t in toks:
            freq[t] = freq.get(t, 0) + 1
        ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
        return [w for w, _ in ranked[:80]]

    def calculate_keyword_match(
        self, resume_text: str, job_description: str
    ) -> Tuple[List[str], List[str], float]:
        r_kw = set(self.extract_keywords(resume_text))
        j_kw = self.extract_keywords(job_description)
        matched: List[str] = []
        missing: List[str] = []
        for kw in j_kw:
            if kw in r_kw:
                matched.append(kw)
                continue
            best = 0
            for rw in r_kw:
                best = max(best, fuzz.ratio(kw, rw))
            if best >= 88:
                matched.append(kw)
            else:
                missing.append(kw)
        if not j_kw:
            return [], [], 0.0
        score = round(100.0 * len(matched) / len(j_kw), 1)
        return matched, missing, score

    _SKILL_LEXICON = (
        "python java javascript typescript go rust c++ c# ruby php swift kotlin scala r "
        "react angular vue node django flask fastapi spring kubernetes docker aws azure "
        "gcp terraform ansible jenkins git linux sql postgres mysql mongodb redis kafka "
        "pandas numpy pytorch tensorflow sklearn mlops graphql rest api agile scrum"
    )

    def extract_skills_from_text(self, text: str) -> List[str]:
        found: set[str] = set()
        lower = text.lower()
        for term in self._SKILL_LEXICON.split():
            if len(term) < 2:
                continue
            if re.search(rf"\b{re.escape(term)}\b", lower):
                found.add(term)
        for m in re.findall(r"\b[A-Z][a-z]+(?:\.js|#)?\b", text):
            if len(m) > 2:
                found.add(m)
        return sorted(found)
