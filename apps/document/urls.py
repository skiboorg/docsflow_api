from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.document.views.document import DocumentTagViewSet, DocumentTypeViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r'document-tags', DocumentTagViewSet, basename='document-tag')
router.register(r'document-types', DocumentTypeViewSet, basename='document-type')
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
]