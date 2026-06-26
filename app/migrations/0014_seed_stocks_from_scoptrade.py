from django.db import migrations


STOCKS = [
    # (symbol, name, is_featured, cloudinary_public_id)
    ('AAPL',  'Apple Inc.',                        False, 'stock_images/bxtekitxhazxrve2jub1'),
    ('AMD',   'Advanced Micro Devices Inc.',        False, 'stock_images/iaimlkp4vn3yvpcouwvg'),
    ('AMZN',  'Amazon.com, Inc.',                  False, 'stock_images/u6cevw9xifqnqljyvnjb'),
    ('ARM',   'Arm Holdings plc',                  False, 'stock_images/zanmtil1nppyws0ijk58'),
    ('AVGO',  'Broadcom.',                          False, 'stock_images/i4fuhdxallkzmwfg9jkx'),
    ('CIEN',  'Ciena',                             False, 'stock_images/aeyzvfeul7zonfztemqu'),
    ('CRWV',  'CoreWeave, Inc.',                   False, 'stock_images/coey5tkt3wiyg5wcizdk'),
    ('DELL',  'Dell Technologies Inc.',            False, 'stock_images/yivghacjv9zz6lagl2go'),
    ('GOOGL', 'Alphabet Inc.',                     False, 'stock_images/msfuoyqitdih2f08tmbb'),
    ('INTC',  'Intel Corp.',                       False, 'stock_images/v5qoozxfb4iyhp7kbewk'),
    ('LITE',  'Lumentum Holdings Inc.',            False, 'stock_images/of7ozpk2cmc0mpaucena'),
    ('META',  'Meta Platforms, Inc.',              False, 'stock_images/c5ff3a4fu322z0b1xcwd'),
    ('MSFT',  'Microsoft Corp.',                   False, 'stock_images/uttrcppq7qpfopdxtvew'),
    ('MU',    'Micron Technology.',                False, 'stock_images/zva9su1pad7oveeif9p8'),
    ('NFLX',  'Netflix, Inc.',                     False, 'stock_images/nlxlpyjgluxr40pjtzda'),
    ('NVDA',  'NVIDIA Corporation',                False, 'stock_images/rkcxc7ex1cf34z7qfd5m'),
    ('PLTR',  'Palantir Technologies Inc.',        False, 'stock_images/uaaiqpxik8ihjsocw75r'),
    ('QQQ',   'Invesco QQQ Trust, Series 1',       False, 'stock_images/pwbvsojlspmozho0vlf3'),
    ('SPX',   'S&P 500 Index',                     False, 'stock_images/jcmsa3o5plrrdx6ruivm'),
    ('SPY',   'SPDR S&P 500 ETF TRUST',            False, 'stock_images/ziihneszfdv5qbc3ah82'),
    ('STX',   'Seagate Technology Holdings PLC',   False, 'stock_images/tvzagoepldhgeywfcild'),
    ('TE',    'TE Connectivity',                   False, 'stock_images/ggyyarhnwir85zjymcqp'),
    ('TSLA',  'Tesla, Inc.',                       False, 'stock_images/ies5wlw8aezsysqkx4a7'),
    ('WDC',   'Western Digital Corporation',       False, 'stock_images/qpusoitduhyehzsyqbc8'),
]


def seed_stocks(apps, schema_editor):
    Stock = apps.get_model('app', 'Stock')
    for symbol, name, is_featured, image in STOCKS:
        if not Stock.objects.filter(symbol=symbol).exists():
            Stock.objects.create(
                symbol=symbol,
                name=name,
                image=image,
                price=0,
                change=0,
                change_percent=0,
                volume=0,
                market_cap=0,
                is_active=True,
                is_featured=is_featured,
            )


def unseed_stocks(apps, schema_editor):
    Stock = apps.get_model('app', 'Stock')
    symbols = [s[0] for s in STOCKS]
    Stock.objects.filter(symbol__in=symbols).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0013_stock_image_alter_customuser_account_id_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_stocks, unseed_stocks),
    ]
