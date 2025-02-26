from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from ...datamodel.models import CheckListItem, StatusType
from ..validators import ZaakTypeConceptValidator


class CheckListItemSerializer(ModelSerializer):
    class Meta:
        model = CheckListItem
        fields = (
            "itemnaam",
            "toelichting",
            "vraagstelling",
            "verplicht",
        )


class StatusTypeSerializer(serializers.HyperlinkedModelSerializer):
    catalogus = serializers.HyperlinkedRelatedField(
        source="zaaktype.catalogus",
        read_only=True,
        view_name="catalogus-detail",
        lookup_field="uuid",
    )

    is_eindstatus = serializers.BooleanField(
        read_only=True,
        help_text=_(
            "Geeft aan dat dit STATUSTYPE een eindstatus betreft. Dit "
            "gegeven is afgeleid uit alle STATUSTYPEn van dit ZAAKTYPE "
            "met het hoogste volgnummer."
        ),
    )

    checklistitem_statustype = CheckListItemSerializer(
        required=False, many=True, source="checklistitem"
    )
    zaaktype_identificatie = serializers.SlugRelatedField(
        source="zaaktype",
        read_only=True,
        slug_field="identificatie",
        help_text=_(
            "Unieke identificatie van het ZAAKTYPE binnen de CATALOGUS waarin het ZAAKTYPE voorkomt."
        ),
    )

    class Meta:
        model = StatusType
        fields = (
            "url",
            "omschrijving",
            "omschrijving_generiek",
            "statustekst",
            "zaaktype",
            "catalogus",
            "zaaktype_identificatie",
            "volgnummer",
            "is_eindstatus",
            "informeren",
            "doorlooptijd",
            "toelichting",
            "checklistitem_statustype",
            "eigenschappen",
            "begin_geldigheid",
            "einde_geldigheid",
            "begin_object",
            "einde_object",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "omschrijving": {"source": "statustype_omschrijving"},
            "omschrijving_generiek": {"source": "statustype_omschrijving_generiek"},
            "volgnummer": {"source": "statustypevolgnummer"},
            "zaaktype": {"lookup_field": "uuid"},
            "eigenschappen": {"lookup_field": "uuid"},
            "begin_geldigheid": {"source": "datum_begin_geldigheid"},
            "einde_geldigheid": {"source": "datum_einde_geldigheid"},
            "begin_object": {"source": "datum_begin_object"},
            "einde_object": {"source": "datum_einde_object"},
            "doorlooptijd": {
                "source": "doorlooptijd_status",
                "label": _("doorlooptijd"),
            },
        }
        validators = [ZaakTypeConceptValidator()]
