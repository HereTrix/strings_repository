from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0021_translation_integration_connected_ai'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectaiprovider',
            name='request_timeout',
            field=models.PositiveIntegerField(default=120),
        ),
    ]
