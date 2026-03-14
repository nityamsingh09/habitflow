from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('habits', '0001_initial')]
    operations = [
        migrations.AddField(
            model_name='habit',
            name='is_public',
            field=models.BooleanField(default=True),
        ),
    ]
