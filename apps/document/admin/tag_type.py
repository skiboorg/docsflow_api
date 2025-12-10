from django.contrib import admin
from apps.document.models import DocumentTag, DocumentType


@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_per_page = 20


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name','slug', 'aliases_display', 'applicable_companies_count']
    search_fields = ['name', 'aliases__name']
    filter_horizontal = ['aliases', 'applicable_company_types']
    list_per_page = 20

    def aliases_display(self, obj):
        return ", ".join([alias.name for alias in obj.aliases.all()])

    aliases_display.short_description = 'Алиасы'

    def applicable_companies_count(self, obj):
        return obj.applicable_company_types.count()

    applicable_companies_count.short_description = 'Кол-во компаний'

