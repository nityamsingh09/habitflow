from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerificationToken, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('email', 'full_name', 'is_verified', 'is_staff', 'date_joined')
    list_filter   = ('is_verified', 'is_staff', 'is_active')
    search_fields = ('email', 'full_name')
    ordering      = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = (
        (None,           {'fields': ('email', 'password')}),
        ('Profile',      {'fields': ('full_name', 'avatar_url', 'google_id')}),
        ('Status',       {'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser')}),
        ('Dates',        {'fields': ('date_joined', 'last_login')}),
        ('Permissions',  {'fields': ('groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'is_verified', 'is_staff'),
        }),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display  = ('user', 'token', 'created_at', 'expires_at', 'is_valid')
    search_fields = ('user__email',)
    readonly_fields = ('created_at',)

    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display  = ('user', 'token', 'created_at', 'expires_at', 'used', 'is_valid')
    list_filter   = ('used',)
    search_fields = ('user__email',)
    readonly_fields = ('created_at',)

    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
