from django.contrib import admin

from . import models

@admin.register(models.TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ('name', 'started_at', 'finished_at', 'success')
    readonly_fields = ('name', 'started_at', 'finished_at', 'success', 'output')
