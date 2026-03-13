import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # ── Habit ──────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Habit',
            fields=[
                ('id',           models.BigAutoField(primary_key=True, serialize=False,
                                                     auto_created=True)),
                ('habit_id',     models.CharField(max_length=100, unique=True)),
                ('name',         models.CharField(max_length=200)),
                ('icon',         models.CharField(max_length=20, default='⭐')),
                ('category',     models.CharField(max_length=100, default='General')),
                ('color',        models.CharField(max_length=20, default='#c8ff00')),
                ('is_default',   models.BooleanField(default=False)),
                ('target_days',  models.PositiveIntegerField(null=True, blank=True)),
                ('target_start', models.DateField(null=True, blank=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('user',         models.ForeignKey(
                                     to=settings.AUTH_USER_MODEL,
                                     on_delete=django.db.models.deletion.CASCADE,
                                     related_name='habits',
                                     null=True, blank=True,
                                 )),
            ],
        ),
        # ── HabitLog ───────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='HabitLog',
            fields=[
                ('id',       models.BigAutoField(primary_key=True, serialize=False,
                                                 auto_created=True)),
                ('log_date', models.DateField()),
                ('habit',    models.ForeignKey(
                                 to='habits.Habit',
                                 to_field='habit_id',
                                 on_delete=django.db.models.deletion.CASCADE,
                                 related_name='logs',
                             )),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='habitlog',
            unique_together={('habit', 'log_date')},
        ),
        # ── Badge ──────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id',         models.BigAutoField(primary_key=True, serialize=False,
                                                   auto_created=True)),
                ('badge_id',   models.CharField(max_length=60)),
                ('earned_at',  models.DateField(default=datetime.date.today)),
                ('extra_data', models.JSONField(default=dict, blank=True)),
                ('habit',      models.ForeignKey(
                                   to='habits.Habit',
                                   to_field='habit_id',
                                   on_delete=django.db.models.deletion.CASCADE,
                                   related_name='badges',
                               )),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='badge',
            unique_together={('badge_id', 'habit')},
        ),
    ]
