from django.contrib import admin
from .models import RuleSet, Verification

admin.site.site_header = 'MAPOLY admission screening'

@admin.register(RuleSet)
class RuleSetAdmin(admin.ModelAdmin):
    list_display = ['programme', 'admission_type', 'academic_session', 'minimum_jamb', 'revision', 'active']
    readonly_fields = ['revision', 'updated_at']
    def save_model(self, request, obj, form, change):
        if change:
            obj.revision += 1
        super().save_model(request, obj, form, change)

@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'created_at']
    readonly_fields = ['owner', 'result', 'created_at']
    def has_add_permission(self, request):
        return False
