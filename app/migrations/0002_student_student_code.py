# Generated by Django 5.1.3 on 2024-11-26 08:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='student_code',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
