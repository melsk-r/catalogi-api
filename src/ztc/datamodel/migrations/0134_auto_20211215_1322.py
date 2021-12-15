# Generated by Django 2.2.4 on 2021-12-15 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datamodel", "0133_auto_20211215_1316"),
    ]

    operations = [
        migrations.AlterField(
            model_name="informatieobjecttype",
            name="zaaktypen",
            field=models.ManyToManyField(
                blank=True,
                help_text="ZAAKTYPE met ZAAKen die relevant kunnen zijn voor dit INFORMATIEOBJECTTYPE",
                related_name="informatieobjecttypen",
                through="datamodel.ZaakInformatieobjectType",
                to="datamodel.ZaakType",
                verbose_name="zaaktypen",
            ),
        ),
    ]
