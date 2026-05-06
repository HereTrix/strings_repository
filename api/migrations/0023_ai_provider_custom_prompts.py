from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0022_ai_provider_request_timeout'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectaiprovider',
            name='translation_instructions',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='projectaiprovider',
            name='verification_instructions',
            field=models.TextField(blank=True, default=''),
        ),
    ]
