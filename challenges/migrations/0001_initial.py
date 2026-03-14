import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.CreateModel('Challenge', fields=[
            ('id',            models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('title',         models.CharField(max_length=100)),
            ('description',   models.CharField(blank=True, max_length=300)),
            ('habit_name',    models.CharField(max_length=100)),
            ('habit_icon',    models.CharField(default='🎯', max_length=10)),
            ('duration_days', models.PositiveIntegerField(default=7)),
            ('start_date',    models.DateField()),
            ('end_date',      models.DateField()),
            ('is_public',     models.BooleanField(default=True)),
            ('created_at',    models.DateTimeField(auto_now_add=True)),
            ('creator',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_challenges', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel('ChallengeParticipant', fields=[
            ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('joined_at',  models.DateTimeField(auto_now_add=True)),
            ('completed',  models.BooleanField(default=False)),
            ('challenge',  models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='challenges.challenge')),
            ('user',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='challenge_participations', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AlterUniqueTogether(name='challengeparticipant', unique_together={('challenge','user')}),
        migrations.CreateModel('ChallengeLog', fields=[
            ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('log_date',   models.DateField()),
            ('logged_at',  models.DateTimeField(auto_now_add=True)),
            ('participant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='challenges.challengeparticipant')),
        ]),
        migrations.AlterUniqueTogether(name='challengelog', unique_together={('participant','log_date')}),
    ]
