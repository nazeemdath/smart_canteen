# Generated by Django 5.1.7 on 2025-03-25 10:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checkout', '0003_feedback'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feedback',
            options={'verbose_name': 'Feedback', 'verbose_name_plural': 'Feedbacks'},
        ),
        migrations.AlterField(
            model_name='feedback',
            name='comment',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='order',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='checkout.order'),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='rating',
            field=models.PositiveSmallIntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]),
        ),
    ]
