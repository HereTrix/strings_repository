from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0025_ai_provider_glossary_instructions'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectaiprovider',
            name='translation_memory_instructions',
            field=models.TextField(blank=True, default=''),
        ),
    ]
