from django.contrib import admin
from apps.company.models.company import Company, CompanyType
from apps.company.models.head import CompanyHead, Head
from apps.company.models.founder import CompanyFounder, Founder

@admin.register(CompanyType)
class CompanyTypeAdmin(admin.ModelAdmin):
    list_display = ['name',]

@admin.register(Head)
class HeadAdmin(admin.ModelAdmin):
    list_display = ['fio',]


@admin.register(Founder)
class FounderAdmin(admin.ModelAdmin):
    list_display = ['fio_company', ]


class CompanyHeadInline(admin.TabularInline):
    model = CompanyHead
    extra = 0

class CompanyFounderInline(admin.TabularInline):
    model = CompanyFounder
    extra = 0

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'inn', 'company_type',  'founding_date']
    list_filter = ['company_type', 'founding_date']
    search_fields = ['name', 'inn', ]
    date_hierarchy = 'founding_date'
    inlines = [CompanyHeadInline,CompanyFounderInline]