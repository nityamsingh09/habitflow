from django.contrib import admin
from django.utils.html import format_html
from .models import Habit, HabitLog, Badge, BADGE_DEFINITIONS


class HabitLogInline(admin.TabularInline):
    model   = HabitLog
    extra   = 0
    ordering = ('-log_date',)
    readonly_fields = ('log_date',)


class BadgeInline(admin.TabularInline):
    model   = Badge
    extra   = 0
    readonly_fields = ('badge_id', 'earned_at')


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display   = ('icon_name', 'user', 'category', 'color_swatch', 'is_public', 'is_default', 'created_at')
    list_filter    = ('is_public', 'is_default', 'category')
    search_fields  = ('name', 'user__email', 'habit_id')
    ordering       = ('-created_at',)
    readonly_fields = ('habit_id', 'created_at')
    inlines        = [HabitLogInline, BadgeInline]

    def icon_name(self, obj):
        return f"{obj.icon} {obj.name}"
    icon_name.short_description = 'Habit'

    def color_swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;border-radius:4px;background:{};vertical-align:middle"></span> {}',
            obj.color, obj.color
        )
    color_swatch.short_description = 'Color'


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display  = ('habit', 'get_user', 'log_date')
    list_filter   = ('log_date',)
    search_fields = ('habit__name', 'habit__user__email')
    ordering      = ('-log_date',)
    date_hierarchy = 'log_date'

    def get_user(self, obj):
        return obj.habit.user
    get_user.short_description = 'User'


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display  = ('badge_id', 'get_emoji', 'habit', 'get_user', 'earned_at')
    list_filter   = ('badge_id', 'earned_at')
    search_fields = ('badge_id', 'habit__name', 'habit__user__email')
    ordering      = ('-earned_at',)
    readonly_fields = ('earned_at',)

    BADGE_MAP = {b[0]: (b[2], b[1]) for b in BADGE_DEFINITIONS}

    def get_emoji(self, obj):
        emoji, name = self.BADGE_MAP.get(obj.badge_id, ('🏅', obj.badge_id))
        return f"{emoji} {name}"
    get_emoji.short_description = 'Badge'

    def get_user(self, obj):
        return obj.habit.user
    get_user.short_description = 'User'
