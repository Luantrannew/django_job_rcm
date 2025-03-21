# Generated by Django 5.1.3 on 2024-11-26 08:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CV',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Education',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('university', models.CharField(max_length=100)),
                ('degree', models.CharField(blank=True, max_length=100, null=True)),
                ('start_year', models.IntegerField(blank=True, null=True)),
                ('end_year', models.IntegerField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Experience',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=100)),
                ('role', models.CharField(max_length=100)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                # ('student_code', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('phone', models.CharField(max_length=15)),
                ('study_year', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='EducationinCV',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cv', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.cv')),
                ('education', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.education')),
            ],
        ),
        migrations.CreateModel(
            name='ExperienceinCV',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cv', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.cv')),
                ('experience', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.experience')),
            ],
        ),
        migrations.CreateModel(
            name='SkillinCV',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cv', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.cv')),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.skill')),
            ],
        ),
        migrations.AddField(
            model_name='cv',
            name='student',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.student'),
        ),
    ]
