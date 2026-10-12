import re
from django.db import migrations, models


def deduplicate(apps, schema_editor):
    Verification = apps.get_model('screening', 'Verification')
    seen = set()
    for record in Verification.objects.using(schema_editor.connection.alias).order_by('-created_at', '-id').iterator():
        value = record.result.get('student', {}).get('registration_number')
        key = re.sub(r'[^A-Z0-9]', '', value.upper()) if isinstance(value, str) else ''
        if not key:
            continue
        identity = (record.owner_id, key)
        if identity in seen:
            record.delete()
        else:
            seen.add(identity)
            record.registration_key = key
            record.save(update_fields=['registration_key'])


class Migration(migrations.Migration):
    dependencies = [('screening', '0001_initial')]
    operations = [
        migrations.AddField(model_name='verification', name='registration_key', field=models.CharField(max_length=80, null=True, blank=True, editable=False)),
        migrations.RunPython(deduplicate, migrations.RunPython.noop),
        migrations.AddConstraint(model_name='verification', constraint=models.UniqueConstraint(fields=('owner', 'registration_key'), name='unique_owner_student_screening')),
    ]
