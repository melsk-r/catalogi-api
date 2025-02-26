from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
    ZaakobjectTypes,
)
from vng_api_common.serializers import (
    GegevensGroepSerializer,
    NestedGegevensGroepMixin,
    add_choice_values_help_text,
)
from vng_api_common.validators import ResourceValidator

from ...datamodel.models import ResultaatType
from ..utils.validators import (
    BrondatumArchiefprocedureValidator,
    ProcestermijnAfleidingswijzeValidator,
    ProcesTypeValidator,
)
from ..validators import ZaakTypeConceptValidator


class BrondatumArchiefprocedureSerializer(GegevensGroepSerializer):
    class Meta:
        model = ResultaatType
        gegevensgroep = "brondatum_archiefprocedure"

        extra_kwargs = {"procestermijn": {"allow_null": True}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(Afleidingswijze)
        self.fields["afleidingswijze"].help_text += "\n\n{}".format(
            value_display_mapping
        )

        value_display_mapping = add_choice_values_help_text(ZaakobjectTypes)
        self.fields["objecttype"].help_text += "\n\n{}".format(value_display_mapping)


class ResultaatTypeSerializer(
    NestedGegevensGroepMixin, serializers.HyperlinkedModelSerializer
):
    brondatum_archiefprocedure = BrondatumArchiefprocedureSerializer(
        label=_("Brondatum archiefprocedure"),
        required=False,
        allow_null=True,
        help_text=(
            "Specificatie voor het bepalen van de brondatum voor de "
            "start van de Archiefactietermijn (=brondatum) van het zaakdossier."
        ),
    )

    zaaktype_identificatie = serializers.SlugRelatedField(
        source="zaaktype",
        read_only=True,
        slug_field="identificatie",
        help_text=_(
            "Unieke identificatie van het ZAAKTYPE binnen de CATALOGUS waarin het ZAAKTYPE voorkomt."
        ),
    )
    besluittype_omschrijving = serializers.SlugRelatedField(
        many=True,
        source="besluittype_set",
        read_only=True,
        slug_field="omschrijving",
        help_text=_("Omschrijving van de aard van BESLUITen van het BESLUITTYPE."),
    )

    informatieobjecttype_omschrijving = serializers.SlugRelatedField(
        many=True,
        source="informatieobjecttypen",
        read_only=True,
        slug_field="omschrijving",
        help_text=_(
            "Omschrijving van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )

    class Meta:
        model = ResultaatType
        fields = (
            "url",
            "zaaktype",
            "zaaktype_identificatie",
            "omschrijving",
            "resultaattypeomschrijving",
            "omschrijving_generiek",
            "selectielijstklasse",
            "toelichting",
            "archiefnominatie",
            "archiefactietermijn",
            "brondatum_archiefprocedure",
            "procesobjectaard",
            "catalogus",
            "begin_geldigheid",
            "einde_geldigheid",
            "begin_object",
            "einde_object",
            "indicatie_specifiek",
            "procestermijn",
            "besluittypen",
            "besluittype_omschrijving",
            "informatieobjecttypen",
            "informatieobjecttype_omschrijving",
        )
        extra_kwargs = {
            "url": {"lookup_field": "uuid"},
            "resultaattypeomschrijving": {
                "validators": [
                    ResourceValidator(
                        "ResultaattypeOmschrijvingGeneriek",
                        settings.REFERENTIELIJSTEN_API_SPEC,
                    )
                ]
            },
            "omschrijving_generiek": {
                "read_only": True,
                "help_text": _(
                    "Waarde van de omschrijving-generiek referentie (attribuut `omschrijving`)"
                ),
            },
            "zaaktype": {"lookup_field": "uuid", "label": _("is van")},
            "selectielijstklasse": {
                "validators": [
                    ResourceValidator("Resultaat", settings.REFERENTIELIJSTEN_API_SPEC)
                ]
            },
            "catalogus": {"lookup_field": "uuid"},
            "begin_object": {"source": "datum_begin_object"},
            "einde_object": {"source": "datum_einde_object"},
            "begin_geldigheid": {
                "source": "datum_begin_geldigheid",
                "help_text": _("De datum waarop de RESULTAATTYPE is ontstaan."),
            },
            "einde_geldigheid": {
                "source": "datum_einde_geldigheid",
                "help_text": _("De datum waarop de RESULTAATTYPE is opgeheven."),
            },
            "besluittypen": {
                "lookup_field": "uuid",
                "source": "besluittype_set",
                "required": False,
            },
            "informatieobjecttypen": {"lookup_field": "uuid", "required": False},
        }
        validators = [
            UniqueTogetherValidator(
                queryset=ResultaatType.objects.all(),
                fields=["zaaktype", "omschrijving"],
            ),
            ProcesTypeValidator("selectielijstklasse"),
            ProcestermijnAfleidingswijzeValidator("selectielijstklasse"),
            BrondatumArchiefprocedureValidator(),
            ZaakTypeConceptValidator(),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        value_display_mapping = add_choice_values_help_text(Archiefnominatie)
        self.fields["archiefnominatie"].help_text += "\n\n{}".format(
            value_display_mapping
        )


class ResultaatTypeCreateSerializer(ResultaatTypeSerializer):
    besluittypen = serializers.ListSerializer(
        child=serializers.CharField(), help_text=""
    )


class ResultaatTypeUpdateSerializer(ResultaatTypeCreateSerializer):
    pass
