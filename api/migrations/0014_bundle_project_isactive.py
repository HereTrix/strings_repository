import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_webhook_endpoint'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove the global unique constraint on version_name
        migrations.AlterField(
            model_name='translationbundle',
            name='version_name',
            field=models.CharField(max_length=50, null=True),
        ),
        # Add project FK
        migrations.AddField(
            model_name='translationbundle',
            name='project',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='bundles',
                to='api.project',
            ),
        ),
        # Add is_active flag
        migrations.AddField(
            model_name='translationbundle',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
        # Add per-project uniqueness on version_name
        migrations.AlterUniqueTogether(
            name='translationbundle',
            unique_together={('project', 'version_name')},
        ),
    ]
