from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from .domain import validate_rules
from .identities import registration_key, screening_key

class RuleSet(models.Model):
    programme = models.CharField(max_length=150)
    academic_session = models.CharField(max_length=30, default='All sessions')
    admission_type = models.CharField(max_length=30, default='ND Full-Time')
    source = models.CharField(max_length=250, blank=True)
    criteria = models.JSONField(default=dict, blank=True)
    minimum_jamb = models.PositiveIntegerField(default=180, null=True, blank=True)
    minimum_credits = models.PositiveIntegerField(default=5)
    max_sittings = models.PositiveSmallIntegerField(default=2, null=True, blank=True)
    allow_combining = models.BooleanField(default=True)
    required_subjects = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def snapshot(self):
        return {key: getattr(self, key) for key in ['id', 'programme', 'academic_session', 'admission_type', 'source', 'criteria', 'minimum_jamb', 'minimum_credits', 'max_sittings', 'allow_combining', 'required_subjects', 'active', 'revision']}

    def clean(self):
        try:
            validate_rules(self.snapshot())
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def __str__(self):
        return f'{self.programme} — {self.admission_type} — {self.academic_session}'

class Verification(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    registration_key = models.CharField(max_length=80, null=True, blank=True, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'registration_key'], name='unique_owner_student_screening')]

    def save(self, *args, **kwargs):
        self.registration_key = screening_key(self.result)
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'registration_key'}
        super().save(*args, **kwargs)
