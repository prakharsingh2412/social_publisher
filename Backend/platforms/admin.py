from django.contrib import admin
from .models import PlatformCredential, Post, PostPlatformResult

@admin.register(PlatformCredential)
class PlatformCredentialAdmin(admin.ModelAdmin):
    list_display = ('platform', 'label', 'is_active', 'updated_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('label',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'status', 'scheduled_at')
    list_filter = ('status', 'scheduled_at')
    search_fields = ('title', 'content')

@admin.register(PostPlatformResult)
class PostPlatformResultAdmin(admin.ModelAdmin):
    list_display = ('post', 'platform', 'status', 'platform_post_id', 'retry_count')
    list_filter = ('platform', 'status')