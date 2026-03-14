import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('accounts', '0001_initial'),
        ('habits',   '0002_habit_is_public'),
    ]
    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id',        models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('username',  models.CharField(blank=True, max_length=40, unique=True)),
                ('bio',       models.CharField(blank=True, max_length=200)),
                ('is_public', models.BooleanField(default=True)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('user',      models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                                    related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id',        models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('follower',  models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='following', to=settings.AUTH_USER_MODEL)),
                ('following', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='followers', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(name='follow', unique_together={('follower','following')}),
        migrations.CreateModel(
            name='FriendRequest',
            fields=[
                ('id',        models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('status',    models.CharField(choices=[('pending','Pending'),('accepted','Accepted'),('declined','Declined')],
                                               default='pending', max_length=10)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('updated_at',models.DateTimeField(auto_now=True)),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='sent_requests', to=settings.AUTH_USER_MODEL)),
                ('to_user',   models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='received_requests', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(name='friendrequest', unique_together={('from_user','to_user')}),
        migrations.CreateModel(
            name='ActivityEvent',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('event_type', models.CharField(choices=[('log','Habit Logged'),('streak','Streak Milestone'),
                                                          ('badge','Badge Earned'),('target','Target Completed')],
                                                 max_length=10)),
                ('meta',       models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('habit',      models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                                  related_name='activity_events', to='habits.habit')),
                ('user',       models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name='activity_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Reaction',
            fields=[
                ('id',        models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('emoji',     models.CharField(max_length=8)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('event',     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='reactions', to='social.activityevent')),
                ('user',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='reactions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(name='reaction', unique_together={('event','user','emoji')}),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id',        models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('text',      models.CharField(max_length=300)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('event',     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='comments', to='social.activityevent')),
                ('user',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                 related_name='comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),
    ]
