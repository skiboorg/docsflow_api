from rest_framework import generics
from rest_framework.response import Response
from django.db.models import Prefetch

from .serializers import MenuItemSerializer
from .models import MenuItem, SubMenuItem

class GetMainMenu(generics.ListAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    pagination_class = None

    def get_queryset(self):
        user = self.request.user

        # Если у пользователя нет роли, возвращаем пустой queryset
        if not user.role:
            return MenuItem.objects.none()

        # Получаем верхние элементы меню, доступные роли пользователя
        submenu_prefetch = Prefetch(
            'menu_items',
            queryset=SubMenuItem.objects.filter(role_can_view=user.role).distinct(),
            to_attr='filtered_subitems'
        )

        # Получаем верхние элементы меню с предзагруженными отфильтрованными подменю
        top_level_menu = MenuItem.objects.filter(
            role_can_view=user.role
        ).distinct().prefetch_related(submenu_prefetch).order_by('order_num')

        return top_level_menu

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            serializer.data,
        )

