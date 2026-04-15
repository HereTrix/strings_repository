from django.db import migrations, models
import django.db.models.deletion
from django.db.models import OuterRef, Subquery


def populate_token_and_name(apps, schema_editor):
    TranslationBundleMap = apps.get_model('api', 'TranslationBundleMap')
    StringToken = apps.get_model('api', 'StringToken')

    # Populate token_id and token_name from the existing translation FK
    TranslationBundleMap.objects.filter(translation__isnull=False).update(
        token_id=Subquery(
            apps.get_model('api', 'Translation')
            .objects.filter(id=OuterRef('translation_id'))
            .values('token_id')[:1]
        ),
        token_name=Subquery(
            StringToken.objects.filter(
                id=Subquery(
                    apps.get_model('api', 'Translation')
                    .objects.filter(id=OuterRef(OuterRef('translation_id')))
                    .values('token_id')[:1]
                )
            ).values('token')[:1]
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_bundle_project_isactive'),
    ]

    operations = [
        # Add created_at to StringToken for reference (nullable for existing rows)
        migrations.AddField(
            model_name='stringtoken',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        # Add token FK (nullable — SET_NULL so deleting a token keeps the bundle map)
        migrations.AddField(
            model_name='translationbundlemap',
            name='token',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='bundle_maps',
                to='api.stringtoken',
            ),
        ),
        # Add token_name to preserve the key string after a token is deleted
        migrations.AddField(
            model_name='translationbundlemap',
            name='token_name',
            field=models.CharField(default='', max_length=200),
        ),
        # Backfill token + token_name from existing translation rows
        migrations.RunPython(populate_token_and_name, migrations.RunPython.noop),
        # Make translation nullable — SET_NULL so deleting a translation keeps the bundle map
        migrations.AlterField(
            model_name='translationbundlemap',
            name='translation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='bundles',
                to='api.translation',
            ),
        ),
    ]
