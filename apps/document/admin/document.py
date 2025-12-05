from django.contrib import admin
from apps.document.models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'company', 'document_type',

    ]
    list_filter = [
        'document_type',

        'company'
    ]
    search_fields = [
        'name', 'company__name', 'document_type__name',

    ]


    list_per_page = 25

