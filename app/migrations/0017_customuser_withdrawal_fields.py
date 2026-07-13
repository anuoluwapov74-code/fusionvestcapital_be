from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0016_remove_stock_app_stock_category_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='withdrawal_limit',
            field=models.DecimalField(
                decimal_places=2,
                default=1000.00,
                help_text='Maximum withdrawal amount per transaction (admin-configurable)',
                max_digits=20,
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='withdrawal_suspended',
            field=models.BooleanField(
                default=False,
                help_text='If True, user is blocked from making any withdrawals',
            ),
        ),
    ]
