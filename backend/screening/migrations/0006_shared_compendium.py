from django.db import migrations
from django.db.models import F


def share_compendium(apps, schema_editor):
    RuleSet = apps.get_model('screening', 'RuleSet')
    RuleSet.objects.filter(source='MAPOLY ND Full-Time compendium supplied by project owner').update(
        admission_type='All Admission Type',
        source='MAPOLY All Admission Type compendium supplied by project owner',
        revision=F('revision') + 1,
    )


class Migration(migrations.Migration):
    dependencies = [('screening', '0005_owner_utme_clarifications')]
    operations = [migrations.RunPython(share_compendium, migrations.RunPython.noop)]
