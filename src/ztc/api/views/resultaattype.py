from django.utils.translation import gettext as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from vng_api_common.caching import conditional_retrieve
from vng_api_common.viewsets import CheckQueryParamsMixin
from rest_framework.response import Response

from ..utils.viewsets import m2m_array_of_str_to_url, remove_invalid_m2m
from ...datamodel.models import ResultaatType
from ..filters import ResultaatTypeFilter
from ..scopes import (
    SCOPE_CATALOGI_FORCED_DELETE,
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from ..serializers import ResultaatTypeSerializer
from .mixins import ForcedCreateUpdateMixin, ZaakTypeConceptMixin


@conditional_retrieve()
@extend_schema_view(
    list=extend_schema(
        summary=_("Alle RESULTAATTYPEn opvragen."),
        description=_("Deze lijst kan gefilterd wordt met query-string parameters."),
    ),
    retrieve=extend_schema(
        summary=_("Een specifieke RESULTAATTYPE opvragen."),
        description=_("Een specifieke RESULTAATTYPE opvragen."),
    ),
    create=extend_schema(
        summary=_("Maak een RESULTAATTYPE aan."),
        description=_(
            "Maak een RESULTAATTYPE aan. Dit kan alleen als het bijbehorende ZAAKTYPE een concept betreft."
        ),
    ),
    update=extend_schema(
        summary=_("Werk een RESULTAATTYPE in zijn geheel bij."),
        description=_(
            "Werk een RESULTAATTYPE in zijn geheel bij. Dit kan alleen als het bijbehorende ZAAKTYPE een concept betreft."
        ),
    ),
    partial_update=extend_schema(
        summary=_("Werk een RESULTAATTYPE deels bij."),
        description=_(
            "Werk een RESULTAATTYPE deels bij. Dit kan alleen als het bijbehorende ZAAKTYPE een concept betreft."
        ),
    ),
    destroy=extend_schema(
        summary=_("Verwijder een RESULTAATTYPE."),
        description=_(
            "Verwijder een RESULTAATTYPE. Dit kan alleen als het bijbehorende ZAAKTYPE een concept betreft."
        ),
    ),
)
class ResultaatTypeViewSet(
    CheckQueryParamsMixin,
    ZaakTypeConceptMixin,
    ForcedCreateUpdateMixin,
    viewsets.ModelViewSet,
):
    global_description = (
        "Opvragen en bewerken van RESULTAATTYPEn van een ZAAKTYPE. Het betreft de indeling of "
        "groepering van resultaten van zaken van hetzelfde ZAAKTYPE naar hun aard, zoals "
        "'verleend', 'geweigerd', 'verwerkt', etc."
    )

    queryset = ResultaatType.objects.all().order_by("-pk")
    serializer_class = ResultaatTypeSerializer
    filter_class = ResultaatTypeFilter
    lookup_field = "uuid"
    required_scopes = {
        "list": SCOPE_CATALOGI_READ,
        "retrieve": SCOPE_CATALOGI_READ,
        "create": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "partial_update": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_WRITE,
        "destroy": SCOPE_CATALOGI_WRITE | SCOPE_CATALOGI_FORCED_DELETE,
    }

    def create(self, request, *args, **kwargs):
        request = m2m_array_of_str_to_url(
            request, ["besluittypen"], self.action
        )
        return super(viewsets.ModelViewSet, self).create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = remove_invalid_m2m(
            self.get_serializer(instance), ["besluittypen"], self.action
        )
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        request = m2m_array_of_str_to_url(request, ["besluittypen"], self.action)
        return super(viewsets.ModelViewSet, self).update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serializer = remove_invalid_m2m(
                serializer, ["besluittypen"], self.action
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        serializer = remove_invalid_m2m(
            serializer, ["besluittypen"], self.action
        )

        return Response(serializer.data)
