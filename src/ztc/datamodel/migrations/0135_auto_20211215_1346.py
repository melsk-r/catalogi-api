# Generated by Django 2.2.4 on 2021-12-15 13:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datamodel", "0134_auto_20211215_1322"),
    ]

    operations = [
        migrations.AddField(
            model_name="roltype",
            name="catalogus",
            field=models.ForeignKey(
                blank=True,
                help_text="URL-referentie naar de CATALOGUS waartoe dit ROLTYPE behoort.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="datamodel.Catalogus",
                verbose_name="catalogus",
            ),
        ),
        migrations.AddField(
            model_name="roltype",
            name="datum_begin_geldigheid",
            field=models.DateField(
                blank=True,
                help_text="De datum waarop het is ontstaan.",
                null=True,
                verbose_name="datum begin geldigheid",
            ),
        ),
        migrations.AddField(
            model_name="roltype",
            name="datum_einde_geldigheid",
            field=models.DateField(
                blank=True,
                help_text="De datum waarop het is opgeheven.",
                null=True,
                verbose_name="datum einde geldigheid",
            ),
        ),
    ]
