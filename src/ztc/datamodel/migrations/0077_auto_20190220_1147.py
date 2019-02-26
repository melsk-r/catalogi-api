# Generated by Django 2.0.9 on 2019-02-20 10:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datamodel', '0076_auto_20190129_1113'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='resultaattype',
            options={'verbose_name': 'Resultaattype', 'verbose_name_plural': 'Resultaattypen'},
        ),
        migrations.RenameField(
            model_name='resultaattype',
            old_name='resultaattypeomschrijving',
            new_name='omschrijving',
        ),
        migrations.AlterUniqueTogether(
            name='resultaattype',
            unique_together={('is_relevant_voor', 'omschrijving')},
        ),
    ]
