"""Apply the project owner's explicit correction; preserve historical results."""
from django.db import migrations


def confirm_sittings(apps, schema_editor):
    RuleSet = apps.get_model('screening', 'RuleSet')
    note = 'The supplied Electrical/Electronics row omits the number in "not more than sittings". Confirm the sitting limit.'
    rules = RuleSet.objects.using(schema_editor.connection.alias).filter(
        programme='Electrical/Electronics Engineering', admission_type='ND Full-Time',
        source='MAPOLY ND Full-Time compendium supplied by project owner')
    for rule in rules:
        criteria = rule.criteria
        criteria['review_notes'] = [n for n in criteria.get('review_notes', []) if n != note]
        criteria['source_text'] = criteria.get('source_text', '').replace('not more than sittings', 'not more than two sittings')
        rule.max_sittings = 2
        rule.criteria = criteria
        rule.revision += 1
        rule.save(update_fields=['max_sittings', 'criteria', 'revision', 'updated_at'])


class Migration(migrations.Migration):
    dependencies = [('screening', '0003_ruleset_admission_type_ruleset_criteria_and_more')]
    operations = [migrations.RunPython(confirm_sittings, migrations.RunPython.noop)]
