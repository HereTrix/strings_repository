from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_add_passkeys'),
    ]

    operations = [
        migrations.AlterField(
            model_name='translationintegration',
            name='api_key',
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='translationintegration',
            name='provider',
            field=models.CharField(
                choices=[
                    ('deepl', 'DeepL'),
                    ('google', 'Google Translate'),
                    ('ai', 'Use Connected AI'),
                ],
                max_length=32,
            ),
        ),
    ]
