# Generated by Django 4.2.3 on 2023-10-30 11:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_alter_projectrole_user_invitation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectAccessToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=16, unique=True)),
                ('permission', models.CharField(choices=[('write', 'Write'), ('read', 'Read')], max_length=10)),
                ('expiration', models.DateTimeField(null=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_tokens', to='api.project')),
            ],
        ),
    ]
