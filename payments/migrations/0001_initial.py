import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.CreateModel('Subscription', fields=[
            ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ('plan',         models.CharField(choices=[('free','Free'),('monthly','Premium Monthly'),('yearly','Premium Yearly')], default='free', max_length=10)),
            ('is_active',    models.BooleanField(default=True)),
            ('started_at',   models.DateTimeField(auto_now_add=True)),
            ('expires_at',   models.DateTimeField(blank=True, null=True)),
            ('razorpay_payment_id',      models.CharField(blank=True, max_length=100)),
            ('razorpay_order_id',        models.CharField(blank=True, max_length=100)),
            ('razorpay_subscription_id', models.CharField(blank=True, max_length=100)),
            ('updated_at',   models.DateTimeField(auto_now=True)),
            ('user',         models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to=settings.AUTH_USER_MODEL)),
        ]),
    ]
