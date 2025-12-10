from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.company.views.company import CompanyViewSet, CompanyTypeViewSet
from apps.company.views.summary import CompanyDocumentMatrixView

router = DefaultRouter()

router.register(r'companies', CompanyViewSet, basename='companies')
router.register(r'company-types', CompanyTypeViewSet, basename='company-types')
urlpatterns = [
    path('company-document-matrix/', CompanyDocumentMatrixView.as_view()),
    path('', include(router.urls)),

]