import re
import logging
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from programs.models import Program
from .models import Lead

logger = logging.getLogger("maslul.leads")

# Israeli mobile: 05x-xxxxxxx | landline: 0x-xxxxxxx | international +972
_ISRAELI_PHONE_RE = re.compile(
    r"^(\+972|972|0)"       # prefix
    r"(5[0-9]|[234689])"    # area code
    r"[\s\-]?"
    r"\d{3}"
    r"[\s\-]?"
    r"\d{4}$"
)

# Rate limiting: max 5 submissions per IP per 10 minutes
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 600  # seconds
DEDUP_WINDOW_DAYS = 30


def _get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "unknown"))


def _is_valid_israeli_phone(phone: str) -> bool:
    stripped = re.sub(r"[\s\-\(\)]", "", phone)
    return bool(_ISRAELI_PHONE_RE.match(stripped))


def _normalize_phone(phone: str) -> str:
    return re.sub(r"[\s\-\(\)]", "", phone)


class LeadCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        ip = _get_client_ip(request)

        # ── Rate limit ────────────────────────────────────────────────────────
        rate_key = f"lead_rate:{ip}"
        count = cache.get(rate_key, 0)
        if count >= RATE_LIMIT_MAX:
            logger.warning(f"Lead rate limit hit from {ip}")
            return Response(
                {"error": "יותר מדי בקשות. נסה שוב בעוד כמה דקות."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        cache.set(rate_key, count + 1, RATE_LIMIT_WINDOW)

        d = request.data
        full_name = (d.get("full_name") or "").strip()
        email = (d.get("email") or "").strip()
        phone = (d.get("phone") or "").strip()

        # ── Required field validation ─────────────────────────────────────────
        if not (full_name and email and phone):
            return Response(
                {"error": "שם מלא, דוא\"ל וטלפון הם שדות חובה"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Phone format validation ───────────────────────────────────────────
        if not _is_valid_israeli_phone(phone):
            return Response(
                {"error": "מספר טלפון לא תקין. יש להזין מספר ישראלי (לדוגמה: 050-0000000)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_phone = _normalize_phone(phone)

        # ── Resolve program ───────────────────────────────────────────────────
        program = None
        program_slug = d.get("program_slug")
        institution_slug = d.get("institution_slug")
        if program_slug and institution_slug:
            program = Program.objects.filter(
                slug=program_slug, institution__slug=institution_slug
            ).first()

        # ── Deduplication: same phone + program within 30 days ───────────────
        dedup_window = timezone.now() - timedelta(days=DEDUP_WINDOW_DAYS)
        dup_qs = Lead.objects.filter(phone__regex=rf"^0?{re.escape(normalized_phone[-9:])}$", created_at__gte=dedup_window)
        if program:
            dup_qs = dup_qs.filter(program=program)
        if dup_qs.exists():
            logger.info(f"Duplicate lead suppressed: phone={normalized_phone} program={program_slug}")
            # Return 200 so the form shows success (don't tell the user it was suppressed)
            return Response({"ok": True}, status=status.HTTP_200_OK)

        Lead.objects.create(
            program=program,
            full_name=full_name,
            email=email,
            phone=normalized_phone,
            psychometric_score=d.get("psychometric_score") or None,
            consent_marketing=bool(d.get("consent_marketing", False)),
            consent_timestamp=timezone.now() if d.get("consent_marketing") else None,
            source_page=(d.get("source_page") or "")[:200],
            utm_data={
                k: d.get(k, "")
                for k in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")
                if d.get(k)
            },
        )

        logger.info(f"New lead: {full_name} ({email}) for program={program_slug} from {ip}")
        return Response({"ok": True}, status=status.HTTP_201_CREATED)
