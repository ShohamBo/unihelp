SCRAPER_CONFIG_FILENAME = "config.yaml"
BS4_HTML_PARSER = "html.parser"

# Claude Haiku — cheapest model, used for translation + classification
TRANSLATION_MODEL = "claude-haiku-4-5-20251001"

# Text is considered Hebrew if this fraction of chars are Hebrew Unicode chars
HEBREW_CHAR_RATIO_THRESHOLD = 0.3

INSTITUTIONS: dict[str, str] = {
    "tau": "אוניברסיטת תל אביב",
    "huji": "האוניברסיטה העברית בירושלים",
    "technion": "הטכניון",
    "bgu": "אוניברסיטת בן גוריון בנגב",
    "biu": "אוניברסיטת בר אילן",
    "haifa": "אוניברסיטת חיפה",
    "reichman": "אוניברסיטת רייכמן",
    "afeka": "אפקה",
    "ono": "מכללת אונו",
    "sce": "סמי שמעון",
}

DEGREE_LEVEL_NORMALIZER: dict[str, str] = {
    "ראשון": "ba",
    "תואר ראשון": "ba",
    "ba": "ba",
    "b.a": "ba",
    "b.sc": "ba",
    "bsc": "ba",
    "שני": "ma",
    "תואר שני": "ma",
    "ma": "ma",
    "m.a": "ma",
    "m.sc": "ma",
    "msc": "ma",
    "דוקטורט": "phd",
    "phd": "phd",
    "ph.d": "phd",
}
