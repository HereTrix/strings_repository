from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_bundle_snapshot_improvements'),
    ]

    operations = [
        migrations.AlterField(
            model_name='translationintegration',
            name='provider',
            field=models.CharField(
                choices=[
                    ('deepl', 'DeepL'),
                    ('google', 'Google Translate'),
                    ('ai', 'Generic AI'),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='translationintegration',
            name='endpoint_url',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='translationintegration',
            name='payload_template',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='translationintegration',
            name='response_path',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='translationintegration',
            name='auth_header',
            field=models.CharField(blank=True, default='Authorization', max_length=100),
        ),
    ]
