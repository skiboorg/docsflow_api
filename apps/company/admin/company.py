from django.contrib import admin
from apps.company.models.company import Company, CompanyType

@admin.register(CompanyType)
class CompanyTypeAdmin(admin.ModelAdmin):
    list_display = ['name',]

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'inn', 'company_type', 'director_name', 'founding_date']
    list_filter = ['company_type', 'founding_date']
    search_fields = ['name', 'inn', 'director_name']
    date_hierarchy = 'founding_date'