import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
        ('habits',   '0002_habit_is_public'),
    ]
    operations = [
        migrations.CreateModel('UserXP', fields=[
            ('id',             models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('total_xp',       models.PositiveIntegerField(default=0)),
            ('streak_freezes', models.PositiveIntegerField(default=0)),
            ('updated_at',     models.DateTimeField(auto_now=True)),
            ('user',           models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='xp', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel('XPTransaction', fields=[
            ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('amount',     models.IntegerField()),
            ('reason',     models.CharField(blank=True, max_length=200)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='xp_transactions', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-created_at']}),
        migrations.CreateModel('DailyQuest', fields=[
            ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('quest_type',   models.CharField(max_length=30)),
            ('quest_date',   models.DateField()),
            ('completed',    models.BooleanField(default=False)),
            ('xp_reward',    models.PositiveIntegerField(default=30)),
            ('completed_at', models.DateTimeField(null=True, blank=True)),
            ('user',         models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_quests', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AlterUniqueTogether(name='dailyquest', unique_together={('user','quest_type','quest_date')}),
        migrations.CreateModel('StreakFreeze', fields=[
            ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('freeze_date', models.DateField()),
            ('used_at',     models.DateTimeField(auto_now_add=True)),
            ('habit',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='freezes', to='habits.habit')),
            ('user',        models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='freezes_used', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AlterUniqueTogether(name='streakfreeze', unique_together={('habit','freeze_date')}),
        migrations.CreateModel('MoodLog', fields=[
            ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('log_date',   models.DateField()),
            ('mood',       models.PositiveSmallIntegerField()),
            ('note',       models.CharField(blank=True, max_length=200)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mood_logs', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AlterUniqueTogether(name='moodlog', unique_together={('user','log_date')}),
    ]
