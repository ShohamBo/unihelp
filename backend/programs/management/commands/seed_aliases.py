from django.core.management.base import BaseCommand

from programs.alias_data import ALIAS_DATA
from programs.models import Program, ProgramAlias


class Command(BaseCommand):
    help = "Seed ProgramAlias table from alias_data.py. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without touching the DB",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created = 0
        skipped_no_program = 0
        skipped_exists = 0

        for institution_slug, name_he_contains, degree_level, aliases in ALIAS_DATA:
            program = Program.objects.filter(
                institution__slug=institution_slug,
                name_he__icontains=name_he_contains,
                degree_level=degree_level,
            ).first()

            if not program:
                skipped_no_program += len(aliases)
                if options["verbosity"] >= 2:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  No program: {institution_slug} | {name_he_contains} | {degree_level}"
                        )
                    )
                continue

            for alias_text in aliases:
                if dry_run:
                    self.stdout.write(f"  [DRY RUN] {alias_text!r} → {program}")
                    created += 1
                    continue

                _, was_created = ProgramAlias.objects.get_or_create(
                    program=program,
                    alias_text=alias_text,
                    defaults={
                        "language": "he" if any("֐" <= c <= "׿" for c in alias_text) else "en",
                        "source_type": "manual",
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped_exists += 1

        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {created} aliases | "
                f"{skipped_exists} already existed | "
                f"{skipped_no_program} skipped (program not in DB yet)"
            )
        )
        if skipped_no_program and not dry_run:
            self.stdout.write(
                "  Tip: run the institution scrapers first, then re-run seed_aliases."
            )
