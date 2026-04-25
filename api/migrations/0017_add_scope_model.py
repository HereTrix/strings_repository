import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_generic_ai_provider'),
    ]

    operations = [
        migrations.CreateModel(
            name='Scope',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scopes', to='api.project')),
                ('tokens', models.ManyToManyField(blank=True, related_name='scopes', to='api.stringtoken')),
            ],
            options={
                'unique_together': {('name', 'project')},
            },
        ),
        migrations.CreateModel(
            name='ScopeImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='scope_images/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('scope', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='api.scope')),
            ],
        ),
    ]
