# Generated by Django 5.1.1 on 2025-04-20 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thriftapp', '0003_alter_role_role_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='role',
            name='role_name',
            field=models.CharField(choices=[('normal_user', 'Normal User'), ('admin', 'Admin')], max_length=20),
        ),
    ]
