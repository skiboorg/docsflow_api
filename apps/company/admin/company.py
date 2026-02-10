from django.contrib import admin
from apps.company.models.company import Company, CompanyType
from apps.company.models.head import CompanyHead, Head

@admin.register(CompanyType)
class CompanyTypeAdmin(admin.ModelAdmin):
    list_display = ['name',]

@admin.register(Head)
class HeadAdmin(admin.ModelAdmin):
    list_display = ['fio',]

class CompanyHeadInline(admin.TabularInline):
    model = CompanyHead
    extra = 0

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'inn', 'company_type',  'founding_date']
    list_filter = ['company_type', 'founding_date']
    search_fields = ['name', 'inn', ]
    date_hierarchy = 'founding_date'
    inlines = [CompanyHeadInline]