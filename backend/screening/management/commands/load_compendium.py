"""Install the supplied compendium without rewriting historical screenings."""
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from screening.compendium import from_source
from screening.domain import validate_rules
from screening.models import RuleSet


class Command(BaseCommand):
    help = 'Load all 28 supplied MAPOLY All Admission Type compendium programmes.'

    def add_arguments(self, parser):
        parser.add_argument('--source', default=str(Path(settings.BASE_DIR).parent / 'compendium.txt'))
        parser.add_argument('--minimum-jamb', type=int, default=100)

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            entries = from_source(Path(options['source']).read_text(encoding='utf-8-sig'))
        except (ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        changed = 0
        for entry in entries:
            entry['cutoff_source'] = {
                'score': 100, 'session': '2025/2026', 'checked_on': '2026-09-27',
                'url': 'https://mapoly.edu.ng/mapoly-begins-processing-of-2025-2026-admission-application-forms/',
            }
            name = entry['programme']
            core = [g['options'][0][0] for g in entry['credit_paths'][0]
                    if g['count'] == 1 and len(g['options']) == 1 and len(g['options'][0]) == 1]
            values = dict(programme=name, academic_session='All sessions', admission_type='All Admission Type',
                          minimum_jamb=options['minimum_jamb'], minimum_credits=5,
                          max_sittings=2,
                          allow_combining=True, required_subjects=[{'subject': s, 'minimum_grade': 'C6'} for s in core],
                          criteria=entry, source='MAPOLY All Admission Type compendium supplied by project owner', active=True)
            values = validate_rules(values)
            rule = RuleSet.objects.filter(programme=name, academic_session='All sessions', source=values['source']).first()
            if rule:
                # Reruns are idempotent and do not undo administrator changes.
                continue
            RuleSet.objects.create(**values)
            changed += 1
        # Archive only identifiable demonstration rules, preserving IDs and all
        # Verification snapshots. Do not deactivate independently authored rules.
        demos = RuleSet.objects.filter(Q(programme__icontains='demo') | Q(academic_session__icontains='demo') |
                                      Q(programme__in=['Computing', 'Business', 'Science'], source='', criteria={})).filter(active=True)
        for rule in demos:
            rule.active = False
            rule.revision += 1
            rule.save(update_fields=['active', 'revision', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(f'Installed {changed} All Admission Type programmes. Demonstration rules archived; history unchanged.'))
