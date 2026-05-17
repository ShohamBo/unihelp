INSTITUTIONS = {
    "tau": {"name_he": "אוניברסיטת תל אביב", "name_en": "Tel Aviv University", "type": "university", "city": "תל אביב", "website": "https://www.tau.ac.il"},
    "huji": {"name_he": "האוניברסיטה העברית בירושלים", "name_en": "Hebrew University of Jerusalem", "type": "university", "city": "ירושלים", "website": "https://www.huji.ac.il"},
    "technion": {"name_he": "הטכניון — מכון טכנולוגי לישראל", "name_en": "Technion", "type": "university", "city": "חיפה", "website": "https://www.technion.ac.il"},
    "bgu": {"name_he": "אוניברסיטת בן-גוריון בנגב", "name_en": "Ben-Gurion University of the Negev", "type": "university", "city": "באר שבע", "website": "https://www.bgu.ac.il"},
    "biu": {"name_he": "אוניברסיטת בר-אילן", "name_en": "Bar-Ilan University", "type": "university", "city": "רמת גן", "website": "https://www.biu.ac.il"},
    "haifa": {"name_he": "אוניברסיטת חיפה", "name_en": "University of Haifa", "type": "university", "city": "חיפה", "website": "https://www.haifa.ac.il"},
    "reichman": {"name_he": "אוניברסיטת רייכמן", "name_en": "Reichman University", "type": "university", "city": "הרצליה", "website": "https://www.runi.ac.il"},
    "openu": {"name_he": "האוניברסיטה הפתוחה", "name_en": "Open University of Israel", "type": "university", "city": "רעננה", "website": "https://www.openu.ac.il"},
    "sapir": {"name_he": "מכללת ספיר", "name_en": "Sapir College", "type": "mechlala_academic", "city": "שדרות", "website": "https://www.sapir.ac.il"},
    "ruppin": {"name_he": "המכללה האקדמית רופין", "name_en": "Ruppin Academic Center", "type": "mechlala_academic", "city": "עמק חפר", "website": "https://www.ruppin.ac.il"},
    "afeka": {"name_he": "אפקה — המכללה האקדמית להנדסה בתל-אביב", "name_en": "Afeka College of Engineering", "type": "mechlala_academic", "city": "תל אביב", "website": "https://www.afeka.ac.il"},
    "shenkar": {"name_he": "שנקר — הנדסה. עיצוב. אמנות", "name_en": "Shenkar College", "type": "mechlala_academic", "city": "רמת גן", "website": "https://www.shenkar.ac.il"},
    "hadassah": {"name_he": "המכללה האקדמית הדסה", "name_en": "Hadassah Academic College", "type": "mechlala_academic", "city": "ירושלים", "website": "https://www.hadassah.ac.il"},
    "achva": {"name_he": "מכללת אחוה", "name_en": "Achva Academic College", "type": "mechlala_academic", "city": "שמשון", "website": "https://www.achva.ac.il"},
}

KNOWN_SLUGS = frozenset(INSTITUTIONS)


def get_name_he(slug: str) -> str:
    return INSTITUTIONS.get(slug, {}).get("name_he", slug)


def get_city(slug: str) -> str:
    return INSTITUTIONS.get(slug, {}).get("city", "")
