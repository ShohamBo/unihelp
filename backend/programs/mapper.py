import hashlib
import json
import logging
from dataclasses import dataclass

from django.core.cache import cache
from rapidfuzz import fuzz, process

from .normalizer import normalize_text, detect_institution_slug, strip_institution_refs

logger = logging.getLogger("maslul.mapper")

CACHE_TTL = 30 * 24 * 3600      # 30 days
FUZZY_THRESHOLD = 92             # minimum WRatio score for Tier 2
FUZZY_CANDIDATES = 10            # corpus entries to consider in Tier 2
LLM_CANDIDATE_LIMIT = 5         # top candidates passed to Haiku
CONTEXT_CONFIDENCE_FLOOR = 0.85  # below this, map_with_context re-tries with LLM


@dataclass
class MapResult:
    program: object | None   # programs.models.Program, typed loosely to avoid import cycle
    confidence: float        # 0.0–1.0
    tier: str                # 'exact' | 'fuzzy' | 'llm' | 'none'
    normalized_input: str


class ProgramMapper:
    """
    Three-tier resolver: free-text mention → canonical Program + confidence.

    Tier 1 – exact match against in-memory alias table        (< 1 µs)
    Tier 2 – rapidfuzz WRatio against full alias corpus       (< 5 ms)
    Tier 3 – Claude Haiku classification (last resort)        (~ 500 ms, cached)

    All results are cached in Redis for 30 days so Tier 3 fires at most once
    per unique (text, institution_hint) pair.
    """

    def __init__(self):
        self._alias_map: dict[str, int] = {}          # normalized_alias → program_id
        self._corpus: list[tuple[str, int]] = []      # [(normalized_text, program_id)]
        self._programs: dict[int, object] = {}        # program_id → Program instance
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def map_text(self, text: str, institution_hint: str | None = None) -> MapResult:
        """
        Resolve a free-text program mention to a canonical Program.
        institution_hint: institution slug ('tau', 'huji', …) if derivable from context.
        Returns MapResult(program=None, confidence=0.0, tier='none') on failure.
        """
        self._ensure_loaded()
        normalized = normalize_text(text)
        inst = institution_hint or detect_institution_slug(text) or ""

        cache_key = self._cache_key(normalized, inst)
        if (cached := self._from_cache(cache_key)) is not None:
            _stat("cache_hit")
            return cached

        # Try without institution stripped, then with
        for search_text in _search_variants(normalized):
            result = self._tier1(search_text, inst)
            if result:
                self._store_cache(cache_key, result)
                _stat("tier1")
                return result

            result = self._tier2(search_text, inst)
            if result:
                self._store_cache(cache_key, result)
                _stat("tier2")
                return result

        result = self._tier3(text, normalized, inst)
        self._store_cache(cache_key, result)
        _stat(result.tier)
        return result

    def map_with_context(
        self,
        text: str,
        surrounding_text: str,
        institution_hint: str | None = None,
    ) -> MapResult:
        """
        Like map_text, but uses surrounding_text as extra LLM context when
        Tier 1/2 confidence is below CONTEXT_CONFIDENCE_FLOOR.
        """
        result = self.map_text(text, institution_hint)
        if result.confidence >= CONTEXT_CONFIDENCE_FLOOR:
            return result
        # Re-run Tier 3 with full context
        return self._tier3(text, normalize_text(text), institution_hint or "", context=surrounding_text)

    def reload(self):
        """Force reload from DB — call after bulk alias inserts."""
        self._loaded = False
        self._ensure_loaded()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_loaded(self):
        if not self._loaded:
            self._load_from_db()

    def _load_from_db(self):
        from .models import ProgramAlias, Program

        self._alias_map.clear()
        self._corpus.clear()
        self._programs.clear()

        for alias in ProgramAlias.objects.select_related("program").iterator():
            norm = normalize_text(alias.alias_text)
            self._alias_map.setdefault(norm, alias.program_id)
            self._corpus.append((norm, alias.program_id))
            self._programs.setdefault(alias.program_id, alias.program)

        for prog in Program.objects.iterator():
            self._programs.setdefault(prog.id, prog)
            for text in filter(None, [prog.name_he, prog.name_en]):
                norm = normalize_text(text)
                self._alias_map.setdefault(norm, prog.id)
                self._corpus.append((norm, prog.id))

        self._loaded = True
        logger.info(
            "ProgramMapper loaded: %d alias entries, %d programs",
            len(self._corpus),
            len(self._programs),
        )

    def _cache_key(self, normalized: str, inst: str) -> str:
        digest = hashlib.md5(f"{normalized}|{inst}".encode()).hexdigest()
        return f"mapper:{digest}"

    def _from_cache(self, key: str) -> MapResult | None:
        raw = cache.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        program = self._programs.get(data["pid"]) if data["pid"] else None
        return MapResult(program=program, confidence=data["conf"], tier=data["tier"], normalized_input=data["norm"])

    def _store_cache(self, key: str, result: MapResult):
        data = {
            "pid": result.program.id if result.program else None,
            "conf": result.confidence,
            "tier": result.tier,
            "norm": result.normalized_input,
        }
        cache.set(key, json.dumps(data), timeout=CACHE_TTL)

    def _matches_inst(self, program_id: int, inst: str) -> bool:
        if not inst:
            return True
        prog = self._programs.get(program_id)
        return prog is None or getattr(prog, "institution_slug", "") == inst

    def _tier1(self, normalized: str, inst: str) -> MapResult | None:
        pid = self._alias_map.get(normalized)
        if pid and self._matches_inst(pid, inst):
            return MapResult(
                program=self._programs.get(pid),
                confidence=1.0,
                tier="exact",
                normalized_input=normalized,
            )
        return None

    def _tier2(self, normalized: str, inst: str) -> MapResult | None:
        if not self._corpus:
            return None
        corpus_texts = [t for t, _ in self._corpus]
        matches = process.extract(normalized, corpus_texts, scorer=fuzz.WRatio, limit=FUZZY_CANDIDATES)
        for match_text, score, idx in matches:
            if score < FUZZY_THRESHOLD:
                break
            _, pid = self._corpus[idx]
            if self._matches_inst(pid, inst):
                return MapResult(
                    program=self._programs.get(pid),
                    confidence=round(score / 100.0, 3),
                    tier="fuzzy",
                    normalized_input=normalized,
                )
        return None

    def _tier3(self, original: str, normalized: str, inst: str, context: str = "") -> MapResult:
        candidates = self._llm_candidates(normalized, inst)
        if not candidates:
            return MapResult(program=None, confidence=0.0, tier="none", normalized_input=normalized)
        try:
            pid = _call_haiku(original, candidates, context)
            if pid and pid in self._programs:
                return MapResult(
                    program=self._programs[pid],
                    confidence=0.75,
                    tier="llm",
                    normalized_input=normalized,
                )
        except Exception as e:
            logger.error("Tier 3 LLM failed for '%s': %s", original, e)
        return MapResult(program=None, confidence=0.0, tier="none", normalized_input=normalized)

    def _llm_candidates(self, normalized: str, inst: str) -> list[dict]:
        corpus_texts = [t for t, _ in self._corpus]
        matches = process.extract(normalized, corpus_texts, scorer=fuzz.WRatio, limit=20)
        seen: set[int] = set()
        out = []
        for _, _, idx in matches:
            _, pid = self._corpus[idx]
            if pid in seen:
                continue
            if not self._matches_inst(pid, inst):
                continue
            seen.add(pid)
            prog = self._programs.get(pid)
            if prog:
                out.append({
                    "id": pid,
                    "name_he": prog.name_he,
                    "name_en": getattr(prog, "name_en", ""),
                    "institution": getattr(prog, "institution_slug", ""),
                    "degree_level": getattr(prog, "degree_level", ""),
                })
            if len(out) >= LLM_CANDIDATE_LIMIT:
                break
        return out


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _search_variants(normalized: str) -> list[str]:
    """Return search strings to try: raw normalized, then with institution refs stripped."""
    stripped = strip_institution_refs(normalized)
    variants = [normalized]
    if stripped and stripped != normalized:
        variants.append(stripped)
    return variants


def _call_haiku(text: str, candidates: list[dict], context: str = "") -> int | None:
    import anthropic
    client = anthropic.Anthropic()
    options = "\n".join(
        f"{i + 1}. {c['name_he']} ({c['name_en']}) | {c['institution']} | {c['degree_level']} | ID:{c['id']}"
        for i, c in enumerate(candidates)
    )
    ctx_line = f"הקשר נוסף: {context}\n" if context else ""
    prompt = (
        f"המשתמש הזכיר תוכנית לימודים: \"{text}\"\n"
        f"{ctx_line}"
        f"תוכניות אפשריות:\n{options}\n\n"
        f"ענה רק במספר (1–{len(candidates)}) של התוכנית הנכונה, או 0 אם אף אחת לא מתאימה."
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        choice = int(msg.content[0].text.strip())
        if 1 <= choice <= len(candidates):
            return candidates[choice - 1]["id"]
    except (ValueError, IndexError):
        pass
    return None


def _stat(tier: str):
    """Best-effort Redis counter increment for mapper stats dashboard."""
    try:
        key = f"mapper_stats:{tier}"
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=None)
    except Exception:
        pass


# Module-level singleton — loaded lazily on first call
program_mapper = ProgramMapper()
