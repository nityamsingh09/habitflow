from django.contrib import admin
from .models import UserProfile, Follow, FriendRequest, ActivityEvent, Reaction, Comment


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('username', 'user', 'bio', 'is_public', 'created_at')
    list_filter   = ('is_public',)
    search_fields = ('username', 'user__email', 'bio')
    ordering      = ('-created_at',)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display  = ('follower', 'following', 'created_at')
    search_fields = ('follower__email', 'following__email')
    ordering      = ('-created_at',)


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display  = ('from_user', 'to_user', 'status', 'created_at', 'updated_at')
    list_filter   = ('status',)
    search_fields = ('from_user__email', 'to_user__email')
    ordering      = ('-created_at',)


class ReactionInline(admin.TabularInline):
    model   = Reaction
    extra   = 0
    readonly_fields = ('user', 'emoji', 'created_at')


class CommentInline(admin.TabularInline):
    model   = Comment
    extra   = 0
    readonly_fields = ('user', 'text', 'created_at')


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display  = ('user', 'event_type', 'habit', 'created_at', 'reaction_count', 'comment_count')
    list_filter   = ('event_type', 'created_at')
    search_fields = ('user__email', 'habit__name')
    ordering      = ('-created_at',)
    readonly_fields = ('created_at',)
    inlines       = [ReactionInline, CommentInline]

    def reaction_count(self, obj):
        return obj.reactions.count()
    reaction_count.short_description = '👍 Reactions'

    def comment_count(self, obj):
        return obj.comments.count()
    comment_count.short_description = '💬 Comments'


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'emoji', 'event', 'created_at')
    search_fields = ('user__email',)
    ordering      = ('-created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('user', 'short_text', 'event', 'created_at')
    search_fields = ('user__email', 'text')
    ordering      = ('-created_at',)

    def short_text(self, obj):
        return obj.text[:60] + ('…' if len(obj.text) > 60 else '')
    short_text.short_description = 'Comment'

from .models import GlobalMessage, DirectMessage

@admin.register(GlobalMessage)
class GlobalMessageAdmin(admin.ModelAdmin):
    list_display  = ('user','short_text','created_at')
    search_fields = ('user__email','text')
    ordering      = ('-created_at',)
    def short_text(self, obj): return obj.text[:60]
    short_text.short_description = 'Message'

@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display  = ('sender','recipient','short_text','read','created_at')
    search_fields = ('sender__email','recipient__email','text')
    list_filter   = ('read',)
    ordering      = ('-created_at',)
    def short_text(self, obj): return obj.text[:60]
    short_text.short_description = 'Message'
