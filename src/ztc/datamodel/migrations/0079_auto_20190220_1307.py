# Generated by Django 2.0.9 on 2019-02-20 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datamodel', '0078_auto_20190220_1148'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultaattype',
            name='omschrijving_generiek',
            field=models.URLField(default='', help_text='Algemeen gehanteerde omschrijving van de aard van resultaten van het RESULTAATTYPE. Dit moet een URL-referentie zijn naar de referenlijst van genrieke resultaattypeomschrijvingen.', max_length=1000, verbose_name='omschrijving generiek'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='resultaattype',
            name='procesobjectaard',
            field=models.TextField(default='', help_text='Omschrijving van het object, subject of gebeurtenis waarop, vanuit archiveringsoptiek, het resultaattype bij zaken van dit type betrekking heeft.', max_length=200, verbose_name='procesobjectaard'),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='resultaattype',
            name='resultaattypeomschrijving_generiek',
        ),
        migrations.AlterUniqueTogether(
            name='resultaattype',
            unique_together={('is_relevant_voor', 'omschrijving', 'procesobjectaard')},
        ),
    ]
