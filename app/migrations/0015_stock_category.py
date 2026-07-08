from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0014_seed_stocks_from_scoptrade'),
    ]

    operations = [
        migrations.AddField(
            model_name='stock',
            name='category',
            field=models.CharField(
                choices=[
                    ('stock',   'Stock'),
                    ('crypto',  'Crypto'),
                    ('etf',     'ETF'),
                    ('indices', 'Indices'),
                ],
                default='stock',
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name='stock',
            index=models.Index(fields=['category'], name='app_stock_category_idx'),
        ),
    ]
