from django.contrib import admin
from apps.document.models import (
    Document,
    UploadedDocument,
    DocumentVersion,

)


# ---------- INLINE ДЛЯ ВЕРСИЙ ДОКУМЕНТА ----------
class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    fields = (
        'version', 'file', 'on_approval', 'approved', 'rejected', 'missing',
        'is_current', 'is_active', 'upload_date',
        'valid_from',
        'valid_until',
        'uploaded_by', 'reviewed_by', 'review_date',
    )
    readonly_fields = ('upload_date',)
    show_change_link = True


# ---------- ДОКУМЕНТ ----------
@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('file',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'company', 'document_type',
        'created_by', 'created_date'
    )
    list_filter = ('company', 'document_type', 'created_date')
    search_fields = ('name', 'description', 'company__name')
    inlines = [DocumentVersionInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'company', 'document_type')
        }),
        ('Создание', {
            'fields': ('created_by', 'created_date'),
        }),
        ('Описание', {
            'fields': ('description',),
        }),
    )
    readonly_fields = ('created_date',)



# ---------- ВЕРСИИ ДОКУМЕНТА ----------
@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'version', 'status_display',
        'upload_date', 'uploaded_by',
        'approved', 'rejected', 'on_approval', 'is_current'
    )
    list_filter = (
        'approved', 'rejected', 'on_approval', 'missing',
        'is_current', 'is_active',
        'upload_date', 'valid_from', 'valid_until',
    )
    search_fields = ('document__name', 'comment', 'rejection_reason')

    fieldsets = (
        ('Основные данные', {
            'fields': (
                'document', 'version', 'file',
                'is_active', 'is_current'
            )
        }),
        ('Статусы', {
            'fields': ('on_approval', 'approved', 'rejected', 'missing')
        }),
        ('Даты', {
            'fields': ('upload_date', 'valid_from', 'valid_until'),
        }),
        ('Ответственные', {
            'fields': ('uploaded_by', 'reviewed_by', 'review_date'),
        }),
        ('Комментарии', {
            'fields': ('comment', 'rejection_reason'),
        }),
    )

    readonly_fields = ('upload_date',)


