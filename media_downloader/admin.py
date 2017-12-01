from django.contrib import admin
from .models import MediaDownloader


class AdminMediaDownloader(admin.ModelAdmin):
    list_display = ('id', 'file', 'title', 'description', 'date')
    search_fields = ('title', )

admin.site.register(MediaDownloader, AdminMediaDownloader)
