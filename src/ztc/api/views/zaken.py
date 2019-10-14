from django.utils.translation import ugettext_lazy as _
from rest_framework import mixins, viewsets
from vng_api_common.notifications.viewsets import (
    NotificationCreateMixin,
    NotificationDestroyMixin,
)
from vng_api_common.viewsets import CheckQueryParamsMixin

from ...datamodel.models import ZaakType
from ..filters import ZaakTypeFilter
from ..kanalen import KANAAL_ZAAKTYPEN
from ..scopes import SCOPE_ZAAKTYPES_READ, SCOPE_ZAAKTYPES_WRITE
from ..serializers import ZaakTypeSerializer
from .mixins import M2MConceptCreateMixin, ConceptDestroyMixin, ConceptFilterMixin
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

# class ZaakObjectTypeViewSet(NestedViewSetMixin, FilterSearchOrderingViewSetMixin,
#                             FlexFieldsMixin, viewsets.ReadOnlyModelViewSet):
#     """
#     retrieve:
#     De objecttypen van objecten waarop een zaak van het ZAAKTYPE betrekking kan hebben.
#
#     list:
#     Een verzameling van ZAAKOBJECTTYPEn.
#     """
#     queryset = ZaakObjectType.objects.all()
#     serializer_class = ZaakObjectTypeSerializer
#
#     required_scopes = {
#         'list': SCOPE_ZAAKTYPES_READ,
#         'retrieve': SCOPE_ZAAKTYPES_READ,
#
#     }


class ZaakTypeViewSet(
    CheckQueryParamsMixin,
    ConceptDestroyMixin,
    ConceptFilterMixin,
    M2MConceptCreateMixin,
    NotificationCreateMixin,
    NotificationDestroyMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    """
    Opvragen en bewerken van ZAAKTYPEn nodig voor ZAKEN in de Zaken API.

    Een ZAAKTYPE beschrijft het geheel van karakteristieke eigenschappen van
    zaken van eenzelfde soort.

    create:
    Maak een ZAAKTYPE aan.

    Maak een ZAAKTYPE aan.

    Er wordt gevalideerd op:
    - geldigheid `catalogus` URL, dit moet een catalogus binnen dezelfde API zijn
    - Uniciteit `catalogus` en `omschrijving`. Dezelfde omeschrijving mag enkel
      opnieuw gebruikt worden als het zaaktype een andere geldigheidsperiode
      kent dan bestaande zaaktypen.

    list:
    Alle ZAAKTYPEn opvragen.

    Deze lijst kan gefilterd wordt met query-string parameters.

    retrieve:
    Een specifieke ZAAKTYPE opvragen.

    Een specifieke ZAAKTYPE opvragen.

    update:
    Werk een ZAAKTYPE in zijn geheel bij.

    Werk een ZAAKTYPE in zijn geheel bij. Dit kan alleen als het een concept
    betreft.

    partial_update:
    Werk een ZAAKTYPE deels bij.

    Werk een ZAAKTYPE deels bij. Dit kan alleen als het een concept betreft.

    destroy:
    Verwijder een ZAAKTYPE.

    Verwijder een ZAAKTYPE. Dit kan alleen als het een concept betreft.
    """

    queryset = ZaakType.objects.prefetch_related(
        "statustypen",
        "zaaktypenrelaties",
        "heeft_relevant_informatieobjecttype",
        "statustypen",
        "resultaattypen",
        "eigenschap_set",
        "roltype_set",
        "besluittype_set",
    ).order_by("-pk")
    serializer_class = ZaakTypeSerializer
    lookup_field = "uuid"
    filterset_class = ZaakTypeFilter
    required_scopes = {
        "list": SCOPE_ZAAKTYPES_READ,
        "retrieve": SCOPE_ZAAKTYPES_READ,
        "create": SCOPE_ZAAKTYPES_WRITE,
        "destroy": SCOPE_ZAAKTYPES_WRITE,
        "publish": SCOPE_ZAAKTYPES_WRITE,
    }
    concept_related_fields = ["besluittype_set"]
    notifications_kanaal = KANAAL_ZAAKTYPEN

    @swagger_auto_schema(request_body=no_body)
    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        instance = self.get_object()

        # check related objects
        besluittypen = instance.besluittype_set.all()
        informatieobjecttypen = instance.heeft_relevant_informatieobjecttype.all()

        for types in [besluittypen, informatieobjecttypen]:
            for relative_type in types:
                if relative_type.concept:
                    msg = _("All related resources should be published")
                    raise PermissionDenied(detail=msg)

        instance.concept = False
        instance.save()

        serializer = self.get_serializer(instance)

        return Response(serializer.data)
