from django.core.management.base import BaseCommand, CommandError
from screening.models import RuleSet

class Command(BaseCommand):
    help = 'Create illustrative rules. Does not overwrite existing rules or create users.'
    def handle(self, *args, **kwargs):
        if RuleSet.objects.exclude(source='').exists():
            raise CommandError('Compendium rules are installed. Use load_compendium; demonstration seeding is disabled.')
        for name, score, subjects in [('Computing — demo', 180, ['English Language', 'Mathematics', 'Physics']), ('Business — demo', 160, ['English Language', 'Mathematics', 'Economics']), ('Science — demo', 190, ['English Language', 'Mathematics', 'Chemistry', 'Biology'])]:
            RuleSet.objects.get_or_create(programme=name, academic_session='Demonstration', defaults={'minimum_jamb': score, 'required_subjects': [{'subject': subject, 'minimum_grade': 'C6'} for subject in subjects]})
        self.stdout.write(self.style.SUCCESS('Demonstration rules ready. These are not approved MAPOLY requirements.'))
