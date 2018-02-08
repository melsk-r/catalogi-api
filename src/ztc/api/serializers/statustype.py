from rest_framework.serializers import (
    HyperlinkedModelSerializer, ModelSerializer
)
from rest_framework_nested.relations import NestedHyperlinkedIdentityField

from ...datamodel.models import CheckListItem, StatusType
from ..utils.rest_flex_fields import FlexFieldsSerializerMixin
from ..utils.serializers import SourceMappingSerializerMixin


class CheckListItemSerializer(SourceMappingSerializerMixin, ModelSerializer):
    class Meta:
        model = CheckListItem
        source_mapping = {
            'naam': 'itemnaam'
        }
        fields = (
            'naam',
            'vraagstelling',
            'verplicht',
            'toelichting',
        )


class StatusTypeSerializer(FlexFieldsSerializerMixin, SourceMappingSerializerMixin, HyperlinkedModelSerializer):
    isVan = NestedHyperlinkedIdentityField(
        view_name='api:zaaktype-detail',
        parent_lookup_kwargs={
            'catalogus_pk': 'is_van__maakt_deel_uit_van__pk',
            'pk': 'is_van__pk'
        },
    )
    heeftVerplichteEigenschap = NestedHyperlinkedIdentityField(
        view_name='api:eigenschap-detail',
        many=True,
        parent_lookup_kwargs={
            'catalogus_pk': 'is_van__maakt_deel_uit_van__pk',
            'zaaktype_pk': 'is_van__pk'
        },
        source='heeft_verplichte_eigenschap',
    )
    # heeftVerplichteZaakObjecttype = NestedHyperlinkedIdentityField(
    #     view_name='api:zaakobjecttype-detail',
    #     many=True,
    #     parent_lookup_kwargs={
    #
    #     },
    #     source='heeft_verplichte_zaakobjecttype',
    # )

    class Meta:
        model = StatusType

        source_mapping = {
            'ingangsdatumObject': 'datum_begin_geldigheid',
            'einddatumObject': 'datum_einde_geldigheid',
            'doorlooptijd': 'doorlooptijd_status',
            'volgnummer': 'statustypevolgnummer',
            'omschrijvingGeneriek': 'statustype_omschrijving_generiek',
            'omschrijving': 'statustype_omschrijving',
            # 'heeftVerplichteEigenschap': 'heeft_verplichte_eigenschap',
        }
        fields = (
            'ingangsdatumObject',
            'einddatumObject',
            'omschrijving',
            'omschrijvingGeneriek',
            'volgnummer',
            'doorlooptijd',
            'checklistitem',
            'informeren',
            'statustekst',
            'toelichting',

            'isVan',
            'heeftVerplichteEigenschap',
            # 'heeftVerplichteZaakObjecttype',

            # TODO:
            # 'roltypen',  deze relatie is gedefinieerd op RolType, niet in xsd, dus Toevoegen aan RolTypeSerializer
            # < element name="heeftVerplichteInformatieobjecttype" type="ztc:STTIOT-antwoord" nillable="true"
        )
