from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_add_glossary'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectaiprovider',
            name='glossary_extraction_instructions',
            field=models.TextField(blank=True, default=''),
        ),
    ]
