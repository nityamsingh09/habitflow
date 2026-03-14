import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('challenges', '0001_initial'), ('accounts', '0001_initial')]
    operations = [
        migrations.CreateModel('ChallengeInvite', fields=[
            ('id',            models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('invited_email', models.EmailField(blank=True)),
            ('status',        models.CharField(choices=[('pending','Pending'),('accepted','Accepted'),('declined','Declined')], default='pending', max_length=20)),
            ('created_at',    models.DateTimeField(auto_now_add=True)),
            ('responded_at',  models.DateTimeField(null=True, blank=True)),
            ('challenge',     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invites', to='challenges.challenge')),
            ('invited_by',    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_invites', to=settings.AUTH_USER_MODEL)),
            ('invited_user',  models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_invites', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AlterUniqueTogether(name='challengeinvite', unique_together={('challenge','invited_user')}),
    ]
