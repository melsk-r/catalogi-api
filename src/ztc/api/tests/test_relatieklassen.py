from unittest import skip

from rest_framework import status
from vng_api_common.constants import VertrouwelijkheidsAanduiding
from vng_api_common.tests import (
    JWTAuthMixin,
    get_operation_url,
    get_validation_errors,
    reverse,
    reverse_lazy,
)

from ztc.datamodel.choices import AardRelatieChoices, InternExtern, RichtingChoices
from ztc.datamodel.models import (
    InformatieObjectType,
    ZaakInformatieobjectType,
    ZaakType,
)
from ztc.datamodel.tests.factories import (
    BesluitTypeFactory,
    InformatieObjectTypeFactory,
    ZaakInformatieobjectTypeArchiefregimeFactory,
    ZaakInformatieobjectTypeFactory,
    ZaakTypeFactory,
)

from ..scopes import (
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from .base import APITestCase


class ZaakInformatieobjectTypeAPITests(APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_WRITE, SCOPE_CATALOGI_READ]

    list_url = reverse_lazy(ZaakInformatieobjectType)

    def test_get_list_default_definitief(self):
        ziot1 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ziot2 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ziot3 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ziot4 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot4_url = reverse(ziot4)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{ziot4_url}")

    def test_get_detail(self):
        ztiot = ZaakInformatieobjectTypeFactory.create()
        url = reverse(ztiot)
        zaaktype_url = reverse(ztiot.zaaktype)
        informatieobjecttype_url = reverse(ztiot.informatieobjecttype)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        expected = {
            "url": f"http://testserver{url}",
            "zaaktype": f"http://testserver{zaaktype_url}",
            "zaaktypeIdentificatie": ztiot.zaaktype.identificatie,
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "informatieobjecttypeOmschrijving": ztiot.informatieobjecttype.omschrijving,
            "volgnummer": ztiot.volgnummer,
            "richting": ztiot.richting,
            "statustype": None,
            "catalogus": f"http://testserver{reverse(ztiot.zaaktype.catalogus)}",
        }
        self.assertEqual(response.json(), expected)

    def test_create_ziot(self):
        zaaktype = ZaakTypeFactory.create(
            identificatie="test", concept=True, datum_einde_geldigheid=None
        )

        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus,
            omschrijving="foo",
            concept=True,
            datum_einde_geldigheid=None,
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ziot = ZaakInformatieobjectType.objects.get(volgnummer=13)

        self.assertEqual(ziot.zaaktype, zaaktype)
        self.assertEqual(ziot.informatieobjecttype, informatieobjecttype)

    def test_create_ziot_on_informatieobjecttype_post(self):
        informatieobjecttype = InformatieObjectTypeFactory.create(
            omschrijving="test", concept=False
        )
        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2019-01-01",
            "informatieobjectcategorie": "test",
        }
        informatieobjecttypen_list_url = get_operation_url("informatieobjecttype_list")

        response = self.client.post(informatieobjecttypen_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ziot = ZaakInformatieobjectType.objects.all()

        self.assertEqual(len(ziot), 2)

    def test_create_two_ziot_on_informatieobjecttype_post(self):
        informatieobjecttype_1 = InformatieObjectTypeFactory.create(
            omschrijving="test", concept=False, datum_begin_geldigheid="2018-01-01"
        )
        zaak = ZaakType.objects.get()
        zaak.concept = False
        zaak.save()

        informatieobjecttype_2 = InformatieObjectTypeFactory.create(
            omschrijving="test", concept=True, datum_begin_geldigheid="2019-01-01"
        )
        informatieobjecttypen_list_url = get_operation_url("informatieobjecttype_list")

        data = {
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "omschrijving": "test",
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "beginGeldigheid": "2020-01-01",
            "informatieobjectcategorie": "test",
        }

        response = self.client.post(informatieobjecttypen_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ziot = ZaakInformatieobjectType.objects.all()
        self.assertEqual(len(ziot), 4)
        ziot_zaaktype_concept = ziot.filter(
            informatieobjecttype__datum_begin_geldigheid="2020-01-01",
            zaaktype__concept=True,
        )
        ziot_zaaktype_non_concept = ziot.filter(
            informatieobjecttype__datum_begin_geldigheid="2020-01-01",
            zaaktype__concept=False,
        )

        self.assertEqual(len(ziot_zaaktype_concept), 1)

        self.assertEqual(len(ziot_zaaktype_non_concept), 1)
        self.assertNotEqual(ziot_zaaktype_concept[0], ziot_zaaktype_non_concept[0])

    def test_create_ziot_on_zaaktype_post(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype_url = get_operation_url(
            "besluittype_retrieve", uuid=besluittype.uuid
        )
        zaaktype = ZaakTypeFactory.create(concept=False, identificatie="test")

        ziot1 = ZaakInformatieobjectTypeFactory.create(zaaktype=zaaktype)

        deelzaaktype1 = ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        deelzaaktype2 = ZaakTypeFactory.create(catalogus=self.catalogus, concept=True)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": "test",
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "deelzaaktypen": [
                f"http://testserver{reverse(deelzaaktype1)}",
                f"http://testserver{reverse(deelzaaktype2)}",
            ],
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2018-01-01",
            "versiedatum": "2018-01-01",
            "verantwoordelijke": "Organisatie eenheid X",
        }

        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ziots = ZaakInformatieobjectType.objects.all()
        self.assertEqual(len(ziots), 2)

    def test_create_two_ziot_on_zaaktype_post(self):
        besluittype = BesluitTypeFactory.create(catalogus=self.catalogus)
        besluittype_url = get_operation_url(
            "besluittype_retrieve", uuid=besluittype.uuid
        )

        informatieobjecttype_1 = InformatieObjectTypeFactory.create(
            omschrijving="test", concept=False, datum_begin_geldigheid="2018-01-01"
        )

        informatieobjecttype_2 = InformatieObjectTypeFactory.create(
            omschrijving="test", concept=True, datum_begin_geldigheid="2019-01-01"
        )
        for query in ZaakType.objects.all():
            query.concept = False
            query.identificatie = "test"
            query.save()

        deelzaaktype1 = ZaakTypeFactory.create(catalogus=self.catalogus, concept=False)
        deelzaaktype2 = ZaakTypeFactory.create(catalogus=self.catalogus, concept=True)

        zaaktype_list_url = get_operation_url("zaaktype_list")
        data = {
            "identificatie": "test",
            "doel": "some test",
            "aanleiding": "some test",
            "indicatieInternOfExtern": InternExtern.extern,
            "handelingInitiator": "indienen",
            "onderwerp": "Klacht",
            "handelingBehandelaar": "uitvoeren",
            "doorlooptijd": "P30D",
            "opschortingEnAanhoudingMogelijk": False,
            "verlengingMogelijk": True,
            "verlengingstermijn": "P30D",
            "publicatieIndicatie": True,
            "verantwoordingsrelatie": [],
            "productenOfDiensten": ["https://example.com/product/123"],
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
            "omschrijving": "some test",
            "deelzaaktypen": [
                f"http://testserver{reverse(deelzaaktype1)}",
                f"http://testserver{reverse(deelzaaktype2)}",
            ],
            "gerelateerdeZaaktypen": [
                {
                    "zaaktype": "http://example.com/zaaktype/1",
                    "aard_relatie": AardRelatieChoices.bijdrage,
                    "toelichting": "test relations",
                }
            ],
            "referentieproces": {"naam": "ReferentieProces 0", "link": ""},
            "catalogus": f"http://testserver{self.catalogus_detail_url}",
            "besluittypen": [f"http://testserver{besluittype_url}"],
            "beginGeldigheid": "2020-01-01",
            "versiedatum": "2020-01-01",
            "verantwoordelijke": "Organisatie eenheid X",
        }

        response = self.client.post(zaaktype_list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ziots = ZaakInformatieobjectType.objects.all()

        self.assertEqual(len(ziots), 4)

        ziot_informatieobjecttype_concept = ziots.filter(
            zaaktype__datum_begin_geldigheid="2020-01-01",
            informatieobjecttype__concept=True,
        )
        ziot_informatieobjecttype_non_concept = ziots.filter(
            zaaktype__datum_begin_geldigheid="2020-01-01",
            informatieobjecttype__concept=False,
        )

        self.assertEqual(len(ziot_informatieobjecttype_concept), 1)

        self.assertEqual(len(ziot_informatieobjecttype_non_concept), 1)
        self.assertNotEqual(
            ziot_informatieobjecttype_concept[0],
            ziot_informatieobjecttype_non_concept[0],
        )

    def test_create_ziot_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False, identificatie="test")
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, omschrijving="foo", concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"test",
            "informatieobjecttype": f"foo",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_ziot_not_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_ziot_fail_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            concept=False, catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_create_ziot_fail_catalogus_mismatch(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(concept=False)
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")

    def test_create_ziot_fail_not_unique(self):
        ziot = ZaakInformatieobjectTypeFactory(volgnummer=1)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=ziot.zaaktype.catalogus
        )
        data = {
            "zaaktype": f"http://testserver.com{reverse(ziot.zaaktype)}",
            "informatieobjecttype": f"http://testserver.com{reverse(informatieobjecttype)}",
            "volgnummer": ziot.volgnummer,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unique")

    def test_delete_ziot(self):
        ziot = ZaakInformatieobjectTypeFactory.create()
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakInformatieobjectType.objects.filter(id=ziot.id))

    def test_delete_ziot_not_concept_zaaktype(self):
        ziot = ZaakInformatieobjectTypeFactory.create(zaaktype__concept=False)
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakInformatieobjectType.objects.filter(id=ziot.id))

    def test_delete_ziot_not_concept_informatieobjecttype(self):
        ziot = ZaakInformatieobjectTypeFactory.create(
            informatieobjecttype__concept=False
        )
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ZaakInformatieobjectType.objects.filter(id=ziot.id))

    def test_delete_ziot_fail_not_concept(self):
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot_url = reverse(ziot)

        response = self.client.delete(ziot_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_update_ziot(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_partial_update_ziot(self):
        zaaktype = ZaakTypeFactory.create()
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 12)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 12)

    def test_partial_update_ziot_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        ziot = ZaakInformatieobjectTypeFactory.create(zaaktype=zaaktype)
        ziot_url = reverse(ziot)
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)

        response = self.client.patch(
            ziot_url, {"informatieobjecttype": informatieobjecttype_url}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")

    def test_update_ziot_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_update_ziot_not_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_update_ziot_not_concept_zaaktype_and_informatieobjecttype_fails(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_partial_update_ziot_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 12)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 12)

    def test_partial_update_ziot_not_concept_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 12)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 12)

    def test_partial_update_ziot_not_concept_zaaktype_and_informatieobjecttype_fails(
        self,
    ):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        response = self.client.patch(ziot_url, {"volgnummer": 12})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-relation")

    def test_full_update_ziot_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create()
        ziot = ZaakInformatieobjectTypeFactory.create(zaaktype=zaaktype)
        ziot_url = reverse(ziot)
        informatieobjecttype = InformatieObjectTypeFactory.create()
        informatieobjecttype_url = reverse(informatieobjecttype)
        zaaktype_url = reverse(ziot.zaaktype)

        response = self.client.put(
            ziot_url,
            {
                "zaaktype": f"http://testserver{zaaktype_url}",
                "informatieobjecttype": informatieobjecttype_url,
                "volgnummer": ziot.volgnummer,
                "richting": ziot.richting,
                "statustype": None,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "relations-incorrect-catalogus")


class ZaakInformatieobjectTypeFilterAPITests(APITestCase):
    maxDiff = None
    list_url = reverse_lazy(ZaakInformatieobjectType)

    def test_filter_zaaktype(self):
        ztiot1, ztiot2 = ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )
        url = f"http://testserver.com{reverse(ztiot1)}"
        zaaktype1_url = reverse(ztiot1.zaaktype)
        zaaktype2_url = reverse(ztiot2.zaaktype)
        zaaktype1_url = f"http://testserver.com{zaaktype1_url}"
        zaaktype2_url = f"http://testserver.com{zaaktype2_url}"

        response = self.client.get(
            self.list_url, {"zaaktype": zaaktype1_url}, HTTP_HOST="testserver.com"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(data[0]["url"], url)
        self.assertEqual(data[0]["zaaktype"], zaaktype1_url)
        self.assertNotEqual(data[0]["zaaktype"], zaaktype2_url)

    def test_filter_informatieobjecttype(self):
        ztiot1, ztiot2 = ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )
        url = f"http://testserver.com{reverse(ztiot1)}"
        informatieobjecttype1_url = reverse(ztiot1.informatieobjecttype)
        informatieobjecttype2_url = reverse(ztiot2.informatieobjecttype)
        informatieobjecttype1_url = f"http://testserver.com{informatieobjecttype1_url}"
        informatieobjecttype2_url = f"http://testserver.com{informatieobjecttype2_url}"

        response = self.client.get(
            self.list_url,
            {"informatieobjecttype": informatieobjecttype1_url},
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]

        self.assertEqual(data[0]["url"], url)
        self.assertEqual(data[0]["informatieobjecttype"], informatieobjecttype1_url)
        self.assertNotEqual(data[0]["informatieobjecttype"], informatieobjecttype2_url)

    def test_filter_ziot_status_alles(self):
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 4)

    def test_filter_ziot_status_concept(self):
        ziot1 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ziot2 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ziot3 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot1_url = reverse(ziot1)
        ziot2_url = reverse(ziot2)
        ziot3_url = reverse(ziot3)

        response = self.client.get(self.list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 3)

        urls = {obj["url"] for obj in data}
        self.assertEqual(
            urls,
            {
                f"http://testserver{ziot1_url}",
                f"http://testserver{ziot2_url}",
                f"http://testserver{ziot3_url}",
            },
        )

    def test_filter_ziot_status_definitief(self):
        ziot1 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=True
        )
        ziot2 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=True
        )
        ziot3 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=True, informatieobjecttype__concept=False
        )
        ziot4 = ZaakInformatieobjectTypeFactory.create(
            zaaktype__concept=False, informatieobjecttype__concept=False
        )
        ziot4_url = reverse(ziot4)

        response = self.client.get(self.list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{ziot4_url}")


class FilterValidationTests(APITestCase):
    def test_unknown_query_params_give_error(self):
        ZaakInformatieobjectTypeFactory.create_batch(2)
        zaakinformatieobjecttype_list_url = get_operation_url(
            "zaakinformatieobjecttype_list"
        )

        response = self.client.get(
            zaakinformatieobjecttype_list_url, {"someparam": "somevalue"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class ZaakInformatieobjectTypePaginationTestCase(APITestCase):
    maxDiff = None
    list_url = reverse_lazy(ZaakInformatieobjectType)

    def test_pagination_default(self):
        ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ZaakInformatieobjectTypeFactory.create_batch(
            2, zaaktype__concept=False, informatieobjecttype__concept=False
        )

        response = self.client.get(self.list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])


@skip("Not MVP yet")
class ZaakInformatieobjectTypeArchiefregimeAPITests(APITestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype__catalogus=self.catalogus,
            informatieobjecttype__catalogus=self.catalogus,
            informatieobjecttype__zaaktypen=None,
            volgnummer=1,
        )

        self.informatieobjecttype = self.ziot.informatieobjecttype
        self.zaaktype = self.ziot.zaaktype

        self.rstiotarc = ZaakInformatieobjectTypeArchiefregimeFactory.create(
            zaak_informatieobject_type=self.ziot,
            resultaattype__is_relevant_voor=self.zaaktype,
            resultaattype__bepaalt_afwijkend_archiefregime_van=None,
        )

        self.resultaattype = self.rstiotarc.resultaattype

        self.rstiotarc_list_url = reverse(
            "api:rstiotarc-list",
            kwargs={
                "version": self.API_VERSION,
                "catalogus_pk": self.catalogus.pk,
                "zaaktype_pk": self.zaaktype.pk,
            },
        )

        self.rstiotarc_detail_url = reverse(
            "api:rstiotarc-detail",
            kwargs={
                "version": self.API_VERSION,
                "catalogus_pk": self.catalogus.pk,
                "zaaktype_pk": self.zaaktype.pk,
                "pk": self.rstiotarc.pk,
            },
        )

    def test_get_list(self):
        response = self.api_client.get(self.rstiotarc_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertTrue("results" in data)
        self.assertEqual(len(data["results"]), 1)

    def test_get_detail(self):
        response = self.api_client.get(self.rstiotarc_detail_url)
        self.assertEqual(response.status_code, 200)

        expected = {
            "url": "http://testserver{}".format(self.rstiotarc_detail_url),
            "gerelateerde": "http://testserver{}".format(
                reverse(
                    "api:informatieobjecttype-detail",
                    args=[
                        self.API_VERSION,
                        self.catalogus.pk,
                        self.informatieobjecttype.pk,
                    ],
                )
            ),
            "rstzdt.archiefactietermijn": 7,
            "rstzdt.archiefnominatie": "",
            "rstzdt.selectielijstklasse": None,
        }
        self.assertEqual(response.json(), expected)


class RolTypeScopeTests(APITestCase, JWTAuthMixin):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_FORCED_WRITE]
    list_url = reverse_lazy(ZaakInformatieobjectType)

    def test_create_ziot_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_ziot_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)

    def test_update_ziot_not_concept_zaaktype_and_informatieobjecttype(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse(zaaktype)
        informatieobjecttype = InformatieObjectTypeFactory.create(
            catalogus=zaaktype.catalogus, concept=False
        )
        informatieobjecttype_url = reverse(informatieobjecttype)
        ziot = ZaakInformatieobjectTypeFactory.create(
            zaaktype=zaaktype, informatieobjecttype=informatieobjecttype
        )
        ziot_url = reverse(ziot)

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "informatieobjecttype": f"http://testserver{informatieobjecttype_url}",
            "volgnummer": 13,
            "richting": RichtingChoices.inkomend,
        }

        response = self.client.put(ziot_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["volgnummer"], 13)

        ziot.refresh_from_db()
        self.assertEqual(ziot.volgnummer, 13)
