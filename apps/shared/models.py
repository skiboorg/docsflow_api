from django.db import models

from apps.common.models import BaseModel
from apps.user.models.roles_and_permissions import Role, Permission


class Page(models.Model):
    label = models.CharField('Название', max_length=255, blank=False, null=True)
    url = models.CharField('Ссылка на страницу', max_length=255, blank=False, null=True)

    def __str__(self):
        return f'{self.label}'

    class Meta:
        ordering = ('label',)
        verbose_name = "Страница"
        verbose_name_plural = "Страницы"


class PagePermission(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='permissions')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permissions = models.ManyToManyField(Permission)


    class Meta:
        verbose_name = "Права ролей на странице"
        verbose_name_plural = "Права ролей на странице"

class MenuItem(models.Model):
    order_num = models.IntegerField(default=1,null=True)
    label = models.CharField('Название', max_length=255, blank=False, null=True)
    icon = models.CharField('Иконка', max_length=255, blank=True, null=True)
    page = models.ForeignKey(Page,
                             on_delete=models.CASCADE,
                             blank=True,
                             help_text='Указать, если нет подменю',
                             null=True)
    role_can_view = models.ManyToManyField(Role,
                                           blank=True,
                                           verbose_name='Кто видит страницу в меню',
                                           related_name='roles_can_view_top_level_menu')


    class Meta:
        ordering = ('order_num', )
        verbose_name = "Элемент меню"
        verbose_name_plural = "Элементы меню"

    def __str__(self):
        return self.label if self.label else self.page.label


class SubMenuItem(models.Model):
    order_num = models.IntegerField(default=1, null=True)
    menu_item = models.ForeignKey(MenuItem,
                                  on_delete=models.CASCADE,
                                  blank=True,
                                  null=True,
                                  related_name='menu_items')
    label = models.CharField('Название', max_length=255, blank=True, null=True)
    icon = models.CharField('Иконка', max_length=255, blank=True, null=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, blank=True, null=True)
    role_can_view = models.ManyToManyField(Role,
                                           blank=True,
                                           verbose_name='Кто видит страницу в меню',
                                           related_name='roles_can_view_sub_level_menu')

    class Meta:
        ordering = ('order_num', )

