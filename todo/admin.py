from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import TodoItem


class TodoItemAdmin(ModelAdmin):
    list_display = ('title', 'status', 'priority', 'due_date', 'organization')
    list_editable = ('status',)
    list_filter = ('status', 'priority', 'organization')
    search_fields = ('title', 'description')


admin.site.register(TodoItem, TodoItemAdmin)