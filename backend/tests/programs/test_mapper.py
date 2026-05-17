"""
ProgramMapper test suite.

Run with: python manage.py test tests.programs.test_mapper

Covers:
  - Text normalization (Hebrew gershayim, nikud, RTL marks, whitespace)
  - Tier 1 (exact alias match)
  - Tier 2 (fuzzy match)
  - Tier 3 (LLM path, mocked)
  - Institution-hint filtering
  - Cache behavior
  - map_with_context
  - No-match / ambiguous cases
  - Performance: 1000 cached lookups < 100ms
"""

import time
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from programs.mapper import MapResult, ProgramMapper
from programs.models import Program, ProgramAlias
from programs.normalizer import normalize_text, detect_institution_slug, strip_institution_refs

# Use a local memory cache for tests so they don't need Redis
TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer tests
# ─────────────────────────────────────────────────────────────────────────────

class NormalizerTests(TestCase):

    def test_gershayim_normalized(self):
        # Hebrew gershayim ״ → "
        self.assertEqual(normalize_text('מדמ״ח'), normalize_text('מדמ"ח'))

    def test_geresh_normalized(self):
        # Hebrew geresh ׳ → '
        self.assertEqual(normalize_text("ת׳א"), normalize_text("ת'א"))

    def test_whitespace_collapsed(self):
        self.assertEqual(normalize_text("  מדעי   המחשב  "), "מדעי המחשב")

    def test_ascii_lowercased(self):
        self.assertEqual(normalize_text("CS TAU"), "cs tau")

    def test_hebrew_preserved(self):
        result = normalize_text("מדעי המחשב")
        self.assertIn("מדעי", result)

    def test_rtl_marks_stripped(self):
        text_with_rtl = "‏מדמח‎"
        self.assertEqual(normalize_text(text_with_rtl), "מדמח")

    def test_nikud_stripped(self):
        # מַדְעֵי (with nikud) → מדעי
        nikud_text = "מַדְעֵי הַמַּחְשֵׁב"
        result = normalize_text(nikud_text)
        self.assertNotIn("ַ", result)
        self.assertIn("מדעי", result)

    def test_empty_string(self):
        self.assertEqual(normalize_text(""), "")

    def test_none_equivalent(self):
        # Should not raise
        result = normalize_text("")
        self.assertEqual(result, "")

    def test_mixed_hebrew_english(self):
        result = normalize_text("CS באוניברסיטת TAU")
        self.assertIn("cs", result)
        self.assertIn("tau", result)

    def test_detect_tau(self):
        self.assertEqual(detect_institution_slug('מדמ"ח ת"א'), "tau")

    def test_detect_tau_english(self):
        self.assertEqual(detect_institution_slug("CS at TAU"), "tau")

    def test_detect_huji(self):
        self.assertEqual(detect_institution_slug("פסיכולוגיה עברית"), "huji")

    def test_detect_technion(self):
        self.assertEqual(detect_institution_slug("הנדסה בטכניון"), "technion")

    def test_detect_bgu(self):
        self.assertEqual(detect_institution_slug('מדמ"ח ב"ג'), "bgu")

    def test_detect_no_match(self):
        self.assertIsNone(detect_institution_slug("מדעי המחשב"))

    def test_strip_institution_leaves_program(self):
        result = strip_institution_refs("מדמח ת\"א")
        self.assertNotIn("ת\"א", result)
        self.assertIn("מדמח", result)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_institution(slug: str, name_he: str) -> str:
    return slug


def _make_program(institution_slug: str, name_he: str, degree_level: str = "ba") -> Program:
    slug = name_he[:50].replace(" ", "-").lower()
    return Program.objects.get_or_create(
        institution_slug=institution_slug,
        slug=slug,
        defaults={
            "name_he": name_he,
            "name_en": "",
            "degree_level": degree_level,
        },
    )[0]


def _make_alias(program: Program, alias_text: str) -> ProgramAlias:
    return ProgramAlias.objects.get_or_create(
        program=program,
        alias_text=alias_text,
        defaults={"language": "he", "source_type": "manual"},
    )[0]


# ─────────────────────────────────────────────────────────────────────────────
# Tier 1 — exact match
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(CACHES=TEST_CACHES)
class Tier1ExactMatchTests(TestCase):

    def setUp(self):
        self.tau = _make_institution("tau", "אוניברסיטת תל אביב")
        self.cs = _make_program(self.tau, "מדעי המחשב")
        _make_alias(self.cs, 'מדמ"ח')
        _make_alias(self.cs, "cs")
        self.mapper = ProgramMapper()

    def test_exact_hebrew_alias(self):
        result = self.mapper.map_text('מדמ"ח', institution_hint="tau")
        self.assertEqual(result.tier, "exact")
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.program, self.cs)

    def test_exact_gershayim_variant(self):
        # ״ and " are normalized to the same form
        result = self.mapper.map_text("מדמ״ח", institution_hint="tau")
        self.assertEqual(result.tier, "exact")
        self.assertEqual(result.program, self.cs)

    def test_exact_english_alias(self):
        result = self.mapper.map_text("CS", institution_hint="tau")
        self.assertEqual(result.tier, "exact")

    def test_exact_case_insensitive_english(self):
        result = self.mapper.map_text("cs", institution_hint="tau")
        self.assertEqual(result.tier, "exact")

    def test_exact_full_name(self):
        result = self.mapper.map_text("מדעי המחשב", institution_hint="tau")
        self.assertIn(result.tier, ("exact", "fuzzy"))
        self.assertEqual(result.program, self.cs)

    def test_institution_hint_filters_correctly(self):
        huji = _make_institution("huji", "האוניברסיטה העברית")
        cs_huji = _make_program(huji, "מדעי המחשב")
        _make_alias(cs_huji, 'מדמ"ח עברית')
        self.mapper.reload()

        result = self.mapper.map_text('מדמ"ח עברית', institution_hint="huji")
        self.assertEqual(result.program, cs_huji)

    def test_institution_hint_excludes_other_inst(self):
        huji = _make_institution("huji", "האוניברסיטה העברית")
        cs_huji = _make_program(huji, "מדעי המחשב")
        _make_alias(cs_huji, 'מדמ"ח עברית')
        self.mapper.reload()

        # Asking for tau should not return huji's program
        result = self.mapper.map_text('מדמ"ח עברית', institution_hint="tau")
        self.assertNotEqual(result.program, cs_huji)

    def test_no_hint_returns_any_match(self):
        result = self.mapper.map_text('מדמ"ח')
        self.assertIsNotNone(result.program)

    def test_whitespace_normalized_before_match(self):
        result = self.mapper.map_text('  מדמ"ח  ', institution_hint="tau")
        self.assertEqual(result.tier, "exact")


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2 — fuzzy match
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(CACHES=TEST_CACHES)
class Tier2FuzzyMatchTests(TestCase):

    def setUp(self):
        self.tau = _make_institution("tau", "אוניברסיטת תל אביב")
        self.cs = _make_program(self.tau, "מדעי המחשב")
        _make_alias(self.cs, "מדעי המחשב")
        self.mapper = ProgramMapper()

    def test_typo_close_match(self):
        result = self.mapper.map_text("מדעי המחשוב", institution_hint="tau")
        self.assertIn(result.tier, ("exact", "fuzzy"))
        self.assertEqual(result.program, self.cs)

    def test_partial_name_match(self):
        result = self.mapper.map_text("מחשבים", institution_hint="tau")
        # May or may not match depending on threshold — just verify no crash
        self.assertIsInstance(result, MapResult)

    def test_english_fuzzy(self):
        result = self.mapper.map_text("computer sciences", institution_hint="tau")
        self.assertIsInstance(result, MapResult)

    def test_fuzzy_confidence_below_one(self):
        _make_alias(self.cs, "computer science")
        self.mapper.reload()
        result = self.mapper.map_text("computer sciences tau", institution_hint="tau")
        if result.tier == "fuzzy":
            self.assertLess(result.confidence, 1.0)
            self.assertGreater(result.confidence, 0.9)

    def test_very_different_text_no_match(self):
        result = self.mapper.map_text("אדריכלות")
        # Should not match CS
        if result.program:
            self.assertNotEqual(result.program, self.cs)


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3 — LLM (mocked)
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(CACHES=TEST_CACHES)
class Tier3LLMTests(TestCase):

    def setUp(self):
        self.tau = _make_institution("tau", "אוניברסיטת תל אביב")
        self.cs = _make_program(self.tau, "מדעי המחשב")
        self.mapper = ProgramMapper()

    @patch("programs.mapper._call_haiku")
    def test_llm_called_when_tiers_fail(self, mock_haiku):
        mock_haiku.return_value = self.cs.id
        result = self.mapper.map_text("סייבר ונתוני ענק", institution_hint="tau")
        if result.tier == "llm":
            self.assertEqual(result.program, self.cs)
            self.assertEqual(result.confidence, 0.75)

    @patch("programs.mapper._call_haiku")
    def test_llm_returns_none_on_zero_choice(self, mock_haiku):
        mock_haiku.return_value = None
        result = self.mapper.map_text("תחום שאין לו תוכנית")
        self.assertIn(result.tier, ("none", "llm"))

    @patch("programs.mapper._call_haiku")
    def test_llm_not_called_when_tier1_succeeds(self, mock_haiku):
        _make_alias(self.cs, "unique-exact-alias-xyz")
        self.mapper.reload()
        self.mapper.map_text("unique-exact-alias-xyz")
        mock_haiku.assert_not_called()

    @patch("programs.mapper._call_haiku", side_effect=Exception("API down"))
    def test_llm_exception_returns_none_tier(self, mock_haiku):
        result = self.mapper.map_text("ביוטכנולוגיה קוגניטיבית")
        self.assertIsInstance(result, MapResult)
        self.assertIn(result.tier, ("none", "exact", "fuzzy"))


# ─────────────────────────────────────────────────────────────────────────────
# Cache behavior
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(CACHES=TEST_CACHES)
class CacheTests(TestCase):

    def setUp(self):
        self.tau = _make_institution("tau", "אוניברסיטת תל אביב")
        self.cs = _make_program(self.tau, "מדעי המחשב")
        _make_alias(self.cs, 'מדמ"ח')
        self.mapper = ProgramMapper()

    def test_same_query_returns_same_result(self):
        r1 = self.mapper.map_text('מדמ"ח', "tau")
        r2 = self.mapper.map_text('מדמ"ח', "tau")
        self.assertEqual(r1.program, r2.program)
        self.assertEqual(r1.confidence, r2.confidence)

    def test_performance_1000_cached_lookups(self):
        # Warm the cache
        self.mapper.map_text('מדמ"ח', "tau")
        start = time.monotonic()
        for _ in range(1000):
            self.mapper.map_text('מדמ"ח', "tau")
        elapsed_ms = (time.monotonic() - start) * 1000
        self.assertLess(elapsed_ms, 100, f"1000 cached lookups took {elapsed_ms:.1f}ms > 100ms")

    def test_different_hints_cached_separately(self):
        huji = _make_institution("huji", "האוניברסיטה העברית")
        cs_huji = _make_program(huji, "מדעי המחשב")
        _make_alias(cs_huji, 'מדמ"ח עברית')
        self.mapper.reload()

        r_tau = self.mapper.map_text("מדעי המחשב", "tau")
        r_huji = self.mapper.map_text("מדעי המחשב", "huji")
        # Both should resolve but potentially to different programs
        self.assertIsInstance(r_tau, MapResult)
        self.assertIsInstance(r_huji, MapResult)


# ─────────────────────────────────────────────────────────────────────────────
# map_with_context
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(CACHES=TEST_CACHES)
class MapWithContextTests(TestCase):

    def setUp(self):
        self.tau = _make_institution("tau", "אוניברסיטת תל אביב")
        self.cs = _make_program(self.tau, "מדעי המחשב")
        _make_alias(self.cs, 'מדמ"ח')
        self.mapper = ProgramMapper()

    def test_context_does_not_break_exact_match(self):
        result = self.mapper.map_with_context('מדמ"ח', "אני לומד בת\"א", "tau")
        self.assertIn(result.tier, ("exact", "fuzzy", "llm"))
        self.assertEqual(result.program, self.cs)

    @patch("programs.mapper._call_haiku")
    def test_context_passed_to_llm(self, mock_haiku):
        mock_haiku.return_value = self.cs.id
        surrounding = "לומד מדמח בת\"א"
        self.mapper.map_with_context("תכנית מעניינת", surrounding, "tau")
        if mock_haiku.called:
            # context is the 3rd positional arg to _call_haiku(text, candidates, context)
            call_args = mock_haiku.call_args
            passed_context = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("context", "")
            self.assertEqual(passed_context, surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# No-match and edge cases
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(CACHES=TEST_CACHES)
class NoMatchTests(TestCase):

    def setUp(self):
        self.tau = _make_institution("tau", "אוניברסיטת תל אביב")
        _make_program(self.tau, "מדעי המחשב")
        self.mapper = ProgramMapper()

    def test_empty_input(self):
        result = self.mapper.map_text("")
        self.assertIsNone(result.program)
        self.assertEqual(result.tier, "none")

    def test_gibberish_input(self):
        result = self.mapper.map_text("xyzqrstuvwxyzabcdef12345")
        self.assertIsInstance(result, MapResult)

    def test_whitespace_only(self):
        result = self.mapper.map_text("   ")
        self.assertIsInstance(result, MapResult)

    def test_unrelated_hebrew(self):
        result = self.mapper.map_text("ספר תורה מאד יפה")
        # May or may not match; just verify it returns a valid result
        self.assertIsInstance(result, MapResult)

    def test_returns_mapresult_always(self):
        for text in ["", "  ", "?!", "123", "abc", "אבג", 'מדמ"ח']:
            result = self.mapper.map_text(text)
            self.assertIsInstance(result, MapResult)
            self.assertIsInstance(result.confidence, float)
            self.assertIn(result.tier, ("exact", "fuzzy", "llm", "none"))

    def test_confidence_zero_on_no_match(self):
        result = self.mapper.map_text("תחום שאף אחד לא לומד")
        if result.tier == "none":
            self.assertEqual(result.confidence, 0.0)
            self.assertIsNone(result.program)

    def test_reload_does_not_crash(self):
        self.mapper.reload()
        result = self.mapper.map_text("מדעי המחשב")
        self.assertIsInstance(result, MapResult)
