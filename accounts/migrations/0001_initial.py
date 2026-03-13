import uuid
import django.utils.timezone
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # auth app must be fully applied before we reference auth.Group / auth.Permission
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # ── User ──────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='User',
            fields=[
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4,
                                                  editable=False, serialize=False)),
                ('password',     models.CharField(max_length=128, verbose_name='password')),
                ('last_login',   models.DateTimeField(blank=True, null=True,
                                                      verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False,
                                                     verbose_name='superuser status')),
                ('email',        models.EmailField(max_length=254, unique=True)),
                ('full_name',    models.CharField(max_length=200, blank=True)),
                ('avatar_url',   models.URLField(blank=True)),
                ('is_active',    models.BooleanField(default=True)),
                ('is_staff',     models.BooleanField(default=False)),
                ('is_verified',  models.BooleanField(default=False)),
                ('google_id',    models.CharField(max_length=200, blank=True,
                                                  null=True, unique=True)),
                ('date_joined',  models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={'abstract': False},
        ),
        # ManyToMany fields must be added AFTER the model exists
        migrations.AddField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(
                blank=True,
                to='auth.Group',
                verbose_name='groups',
                related_name='accounts_user_groups',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(
                blank=True,
                to='auth.Permission',
                verbose_name='user permissions',
                related_name='accounts_user_permissions',
            ),
        ),
        # ── EmailVerificationToken ─────────────────────────────────────────────
        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id',         models.BigAutoField(primary_key=True, serialize=False,
                                                   auto_created=True)),
                ('token',      models.UUIDField(default=uuid.uuid4, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('user',       models.OneToOneField(
                                   to='accounts.User',
                                   on_delete=django.db.models.deletion.CASCADE,
                                   related_name='verification_token',
                               )),
            ],
        ),
        # ── PasswordResetToken ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id',         models.BigAutoField(primary_key=True, serialize=False,
                                                   auto_created=True)),
                ('token',      models.UUIDField(default=uuid.uuid4, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used',       models.BooleanField(default=False)),
                ('user',       models.ForeignKey(
                                   to='accounts.User',
                                   on_delete=django.db.models.deletion.CASCADE,
                                   related_name='reset_tokens',
                               )),
            ],
        ),
    ]
