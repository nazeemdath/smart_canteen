# Generated by Django 5.1.7 on 2025-04-18 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0007_cartitem_discounted_price_cartitem_subtotal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartitem',
            name='discounted_price',
            field=models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=10, null=True),
        ),
    ]
