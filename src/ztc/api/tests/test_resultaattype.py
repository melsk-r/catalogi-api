from copy import deepcopy
from datetime import date, timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

import requests_mock
from dateutil.relativedelta import relativedelta
from relativedeltafield.utils import format_relativedelta
from rest_framework import status
from vng_api_common.constants import (
    BrondatumArchiefprocedureAfleidingswijze as Afleidingswijze,
)
from vng_api_common.tests import (
    JWTAuthMixin,
    TypeCheckMixin,
    get_operation_url,
    get_validation_errors,
    reverse,
    reverse_lazy,
)
from zds_client.tests.mocks import mock_client

from ztc.api.utils.validators import BrondatumArchiefprocedureValidator
from ztc.datamodel.constants import SelectielijstKlasseProcestermijn as Procestermijn
from ztc.datamodel.models import ResultaatType
from ztc.datamodel.tests.factories import ResultaatTypeFactory, ZaakTypeFactory
from ztc.datamodel.tests.factories.besluittype import BesluitTypeFactory
from ztc.datamodel.tests.factories.informatie_objecten import (
    InformatieObjectTypeFactory,
)

from ..scopes import (
    SCOPE_CATALOGI_FORCED_WRITE,
    SCOPE_CATALOGI_READ,
    SCOPE_CATALOGI_WRITE,
)
from .base import APITestCase
from .constants import BrondatumArchiefprocedureExampleMapping as MAPPING

PROCESTYPE_URL = "http://referentielijsten.nl/procestypen/1234"
SELECTIELIJSTKLASSE_URL = "http://example.com/resultaten/1234"
SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL = "http://example.com/resultaten/4321"
SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL = (
    "http://example.com/resultaten/5678"
)

RESULTAATTYPEOMSCHRIJVING_URL = "http://example.com/omschrijving/1"


class ResultaatTypeAPITests(TypeCheckMixin, APITestCase):
    maxDiff = None
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_WRITE, SCOPE_CATALOGI_READ]

    list_url = reverse_lazy(ResultaatType)

    def test_get_list(self):
        ResultaatTypeFactory.create_batch(
            3,
            zaaktype__concept=False,
            procesobjectaard="proces aard",
            catalogus=self.catalogus,
            datum_begin_geldigheid=timezone.now(),
            datum_einde_geldigheid=timezone.now() + timedelta(days=1),
            indicatie_specifiek=False,
            procestermijn=relativedelta(hours=25, day=1),
        )

        response = self.api_client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["results"]
        self.assertEqual(len(data), 3)
        self.assertResponseTypes(
            data[0],
            (
                ("url", str),
                ("zaaktype", str),
                ("omschrijving", str),
                ("resultaattypeomschrijving", str),
                ("omschrijvingGeneriek", str),
                ("selectielijstklasse", str),
                ("toelichting", str),
                ("archiefnominatie", str),
                ("archiefactietermijn", str),
                ("brondatumArchiefprocedure", dict),
                ("procesobjectaard", str),
                ("catalogus", str),
                ("beginGeldigheid", str),
                ("eindeGeldigheid", str),
                ("indicatieSpecifiek", bool),
                ("procestermijn", str),
                ("besluittypen", list),
                ("informatieobjecttypen", list),
            ),
        )

    def test_get_list_default_definitief(self):
        resultaattype1 = ResultaatTypeFactory.create(zaaktype__concept=True)
        resultaattype2 = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")
        resultaattype2_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype2.uuid}
        )

        response = self.client.get(resultaattype_list_url)
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{resultaattype2_url}")

    def test_get_detail(self):
        besluittype = BesluitTypeFactory(catalogus=self.catalogus)
        informatieobjecttype = InformatieObjectTypeFactory(catalogus=self.catalogus)
        resultaattype = ResultaatTypeFactory(
            procesobjectaard="proces aard",
            catalogus=self.catalogus,
            datum_begin_geldigheid=date(2021, 10, 30),
            datum_einde_geldigheid=date(2021, 10, 31),
            indicatie_specifiek=False,
            procestermijn=relativedelta(days=2, hours=5),
            besluittypen=[besluittype],
            informatieobjecttypen=[informatieobjecttype],
        )

        url = reverse(resultaattype)
        zaaktype_url = reverse(
            "zaaktype-detail", kwargs={"uuid": resultaattype.zaaktype.uuid}
        )
        catalogus_url = reverse(
            "catalogus-detail", kwargs={"uuid": self.catalogus.uuid}
        )
        besluittype_url = reverse(
            "besluittype-detail", kwargs={"uuid": besluittype.uuid}
        )
        informatieobjecttype_url = reverse(
            "informatieobjecttype-detail", kwargs={"uuid": informatieobjecttype.uuid}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(
            response_data,
            {
                "url": f"http://testserver{url}",
                "zaaktype": f"http://testserver{zaaktype_url}",
                "omschrijving": resultaattype.omschrijving,
                "resultaattypeomschrijving": resultaattype.resultaattypeomschrijving,
                "omschrijvingGeneriek": resultaattype.omschrijving_generiek,
                "selectielijstklasse": resultaattype.selectielijstklasse,
                "toelichting": "",
                "archiefnominatie": resultaattype.archiefnominatie,
                "archiefactietermijn": "P10Y",
                "brondatumArchiefprocedure": {
                    "afleidingswijze": "",
                    "datumkenmerk": "",
                    "einddatumBekend": False,
                    "objecttype": "",
                    "registratie": "",
                    "procestermijn": None,
                },
                "procesobjectaard": "proces aard",
                "catalogus": f"http://testserver{catalogus_url}",
                "beginGeldigheid": "2021-10-30",
                "eindeGeldigheid": "2021-10-31",
                "beginObject": None,
                "eindeObject": None,
                "indicatieSpecifiek": False,
                "procestermijn": "P2DT5H",
                "besluittypen": [f"http://testserver{besluittype_url}"],
                "besluittypeOmschrijving": [besluittype.omschrijving],
                "informatieobjecttypeOmschrijving": [informatieobjecttype.omschrijving],
                "informatieobjecttypen": [
                    f"http://testserver{informatieobjecttype_url}"
                ],
                "zaaktypeIdentificatie": resultaattype.zaaktype.identificatie,
            },
        )

    def test_resultaattypen_embedded_zaaktype(self):
        resultaattype = ResultaatTypeFactory.create()
        url = f"http://testserver{reverse(resultaattype)}"
        zaaktype_url = reverse(
            "zaaktype-detail", kwargs={"uuid": resultaattype.zaaktype.uuid}
        )

        response = self.client.get(zaaktype_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["resultaattypen"], [url])

    def test_resultaattype_afleidingswijze_procestermijn(self):
        resultaattype = ResultaatTypeFactory.create(
            brondatum_archiefprocedure_afleidingswijze="procestermijn",
            brondatum_archiefprocedure_procestermijn="P5Y",
        )

        url = reverse(resultaattype)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        brondatumArchiefprocedure = response.json()["brondatumArchiefprocedure"]

        afleidingswijze = resultaattype.brondatum_archiefprocedure_afleidingswijze
        procestermijn = resultaattype.brondatum_archiefprocedure_procestermijn

        self.assertEqual(brondatumArchiefprocedure["afleidingswijze"], afleidingswijze)

        # Verify that the procestermijn was serialized correctly
        self.assertEqual(
            brondatumArchiefprocedure["procestermijn"],
            format_relativedelta(procestermijn),
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_resultaattype(self, mock_shape, mock_fetch):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        besluittype = BesluitTypeFactory(
            catalogus=self.catalogus,
            omschrijving="foobarios",
            datum_begin_geldigheid="2021-10-30",
            datum_einde_geldigheid="2022-10-31",
        )

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "beginGeldigheid": "2021-10-30",
            "eindeGeldigheid": "2021-10-31",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "besluittypen": [f"{besluittype.omschrijving}"],
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(
                    self.list_url, data, SERVER_NAME="testserver.com"
                )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resultaattype = response.json()

        self.assertEqual(resultaattype["omschrijvingGeneriek"], "test")
        self.assertEqual(
            resultaattype["zaaktype"], f"http://testserver.com{zaaktype_url}"
        )
        self.assertEqual(
            resultaattype["brondatumArchiefprocedure"]["afleidingswijze"],
            Afleidingswijze.afgehandeld,
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_resultaattype_fail_not_concept_zaaktype(
        self, mock_shape, mock_fetch
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    def test_delete_resultaattype(self):
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype.uuid}
        )

        response = self.client.delete(resultaattype_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResultaatType.objects.filter(id=resultaattype.id))

    def test_delete_resultaattype_fail_not_concept_zaaktype(self):
        resultaattype = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype.uuid}
        )

        response = self.client.delete(resultaattype_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype_fail_not_concept_zaaktype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype_add_relation_to_non_concept_zaaktype_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    def test_partial_update_resultaattype(self):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        response = self.client.patch(resultaattype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

    def test_partial_update_resultaattype_fail_not_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        response = self.client.patch(resultaattype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_partial_update_resultaattype_add_relation_to_non_concept_zaaktype_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create()
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            response = self.client.patch(resultaattype_url, {"zaaktype": zaaktype_url})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "non-concept-zaaktype")


class ResultaatTypeFilterAPITests(APITestCase):
    maxDiff = None

    def test_filter_on_zaaktype(self):
        zt1, zt2 = ZaakTypeFactory.create_batch(2, concept=False)
        rt1 = ResultaatTypeFactory.create(zaaktype=zt1)
        rt1_url = f"http://testserver.com{reverse(rt1)}"
        rt2 = ResultaatTypeFactory.create(zaaktype=zt2)
        rt2_url = f"http://testserver.com{reverse(rt2)}"
        zt1_url = "http://testserver.com{}".format(
            reverse("zaaktype-detail", kwargs={"uuid": zt1.uuid})
        )
        zt2_url = "http://testserver.com{}".format(
            reverse("zaaktype-detail", kwargs={"uuid": zt2.uuid})
        )
        list_url = reverse("resultaattype-list")

        response = self.client.get(
            list_url, {"zaaktype": zt1_url}, HTTP_HOST="testserver.com"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()["results"]
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["url"], rt1_url)
        self.assertEqual(response_data[0]["zaaktype"], zt1_url)
        self.assertNotEqual(response_data[0]["url"], rt2_url)
        self.assertNotEqual(response_data[0]["zaaktype"], zt2_url)

    def test_filter_resultaattype_status_alles(self):
        ResultaatTypeFactory.create(zaaktype__concept=True)
        ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")

        response = self.client.get(resultaattype_list_url, {"status": "alles"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 2)

    def test_filter_resultaattype_status_concept(self):
        resultaattype1 = ResultaatTypeFactory.create(zaaktype__concept=True)
        resultaattype2 = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")
        resultaattype1_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype1.uuid}
        )

        response = self.client.get(resultaattype_list_url, {"status": "concept"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{resultaattype1_url}")

    def test_filter_resultaattype_status_definitief(self):
        resultaattype1 = ResultaatTypeFactory.create(zaaktype__concept=True)
        resultaattype2 = ResultaatTypeFactory.create(zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")
        resultaattype2_url = reverse(
            "resultaattype-detail", kwargs={"uuid": resultaattype2.uuid}
        )

        response = self.client.get(resultaattype_list_url, {"status": "definitief"})
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{resultaattype2_url}")

    def test_filter_zaaktype_identificatie(self):
        resultaattype1 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
        )
        resultaattype2 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
        )

        list_url = reverse("resultaattype-list")
        response = self.client.get(
            list_url, {"zaaktypeIdentificatie": resultaattype1.zaaktype.identificatie}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], f"http://testserver{reverse(resultaattype1)}")

    def test_filter_zaaktype_datum_geldigheid_get_latest_version(self):
        resultaattype1 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
            zaaktype__identificatie="123",
            datum_begin_geldigheid="2020-01-01",
            datum_einde_geldigheid="2020-02-01",
        )
        resultaattype2 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
            zaaktype__identificatie="123",
            datum_begin_geldigheid="2020-02-02",
            datum_einde_geldigheid="2020-03-01",
        )
        resultaattype3 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
            zaaktype__identificatie="123",
            datum_begin_geldigheid="2020-03-02",
        )
        list_url = reverse("resultaattype-list")
        response = self.client.get(
            list_url,
            {
                "datumGeldigheid": "2020-03-05",
                "zaaktypeIdentificatie": "123",
            },
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["beginGeldigheid"], resultaattype3.datum_begin_geldigheid
        )

    def test_filter_zaaktype_datum_geldigheid_get_older_version(self):
        resultaattype1 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
            zaaktype__identificatie="123",
            datum_begin_geldigheid="2020-01-01",
            datum_einde_geldigheid="2020-02-01",
        )
        resultaattype2 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
            zaaktype__identificatie="123",
            datum_begin_geldigheid="2020-02-02",
            datum_einde_geldigheid="2020-03-01",
        )
        resultaattype3 = ResultaatTypeFactory.create(
            zaaktype__concept=False,
            zaaktype__identificatie="123",
            datum_begin_geldigheid="2020-03-02",
        )
        list_url = reverse("resultaattype-list")
        response = self.client.get(
            list_url,
            {
                "datumGeldigheid": "2020-02-15",
                "zaaktypeIdentificatie": "123",
            },
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()["results"]

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["beginGeldigheid"], resultaattype2.datum_begin_geldigheid
        )


class FilterValidationTests(APITestCase):
    def test_unknown_query_params_give_error(self):
        ResultaatTypeFactory.create_batch(2)
        resultaattype_list_url = get_operation_url("resultaattype_list")

        response = self.client.get(resultaattype_list_url, {"someparam": "somevalue"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "unknown-parameters")


class ResultaatTypePaginationTestCase(APITestCase):
    maxDiff = None

    def test_pagination_default(self):
        ResultaatTypeFactory.create_batch(2, zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")

        response = self.client.get(resultaattype_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ResultaatTypeFactory.create_batch(2, zaaktype__concept=False)
        resultaattype_list_url = reverse("resultaattype-list")

        response = self.client.get(resultaattype_list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])


class ResultaatTypeValidationTests(APITestCase):
    list_url = reverse_lazy(ResultaatType)
    RESPONSES = {
        SELECTIELIJSTKLASSE_URL: {
            "url": SELECTIELIJSTKLASSE_URL,
            "procesType": PROCESTYPE_URL,
            "procestermijn": "vast_te_leggen_datum",
        },
        SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL: {
            "url": SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL,
            "procesType": PROCESTYPE_URL,
            "procestermijn": Procestermijn.nihil,
        },
        SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL: {
            "url": SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL,
            "procesType": PROCESTYPE_URL,
            "procestermijn": Procestermijn.ingeschatte_bestaansduur_procesobject,
        },
        # RESULTAATTYPEOMSCHRIJVING_URL: {
        #     'omschrijving': 'test'
        # }
    }

    def _get_selectielijstklasse_url(self, afleidingswijze):
        if afleidingswijze == Afleidingswijze.afgehandeld:
            selectielijstklasse = SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL
        elif afleidingswijze == Afleidingswijze.termijn:
            selectielijstklasse = (
                SELECTIELIJSTKLASSE_PROCESTERMIJN_INGESCHATTE_BESTAANSDUUR_OBJECT_URL
            )
        else:
            selectielijstklasse = SELECTIELIJSTKLASSE_URL
        return selectielijstklasse

    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=False)
    def test_validate_wrong_resultaattypeomschrijving(self, mock_shape, mock_fetch):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": "https://garcia.org/",
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": "P10Y",
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with requests_mock.Mocker() as m:
            m.register_uri(
                "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
            )
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, "resultaattypeomschrijving")
        self.assertEqual(error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_selectielijstklasse_invalid_resource(self):
        zaaktype = ZaakTypeFactory.create(concept=False)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            "http://example.com/resultaten/1234": {"some": "incorrect property"}
        }

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": "http://example.com/resultaten/1234",
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": "P10Y",
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "selectielijstklasse")
        self.assertEqual(error["code"], "invalid-resource")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_selectielijstklasse_procestype_no_match_with_zaaktype_procestype(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": "http://somedifferentprocestypeurl.com/",
                "procestermijn": Procestermijn.nihil,
            }
        }

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "procestype-mismatch")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_nihil_and_afleidingswijze_niet_afgehandeld_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.ander_datumkenmerk,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "identificatie",
                "objecttype": "pand",
                "registratie": "test",
            },
        }

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_empty_and_afleidingswijze_afgehandeld(
        self, mock_shape, mock_fetch
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": "",
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_empty_and_afleidingswijze_termijn(
        self, mock_shape, mock_fetch
    ):
        zaaktype = ZaakTypeFactory.create(selectielijst_procestype=PROCESTYPE_URL)
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.termijn,
                "einddatumBekend": False,
                "procestermijn": "P5Y",
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": "",
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_ingeschatte_bestaansduur_procesobject_and_afleidingswijze_niet_termijn_fails(
        self, *mocks
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.ingeschatte_bestaansduur_procesobject,
            }
        }

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with mock_client(responses):
            response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-afleidingswijze-for-procestermijn")

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_empty_and_afleidingswijze_niet_termijn(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": "",
            }
        }

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": "https://garcia.org/",
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", "https://garcia.org/", json={"omschrijving": "bla"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_datumkenmerk(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["datumkenmerk"] = "identificatie"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.eigenschap,
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.datumkenmerk"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.empty_code
                    )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_datumkenmerk_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["datumkenmerk"] = ""

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.eigenschap,
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.datumkenmerk"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.required_code
                    )
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_einddatum_bekend_true(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["einddatumBekend"] = True

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.afgehandeld,
                    Afleidingswijze.termijn,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.einddatumBekend"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.empty_code
                    )
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_einddatum_bekend_false(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["einddatumBekend"] = False

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_objecttype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["objecttype"] = "pand"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.objecttype"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.empty_code
                    )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_objecttype_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["objecttype"] = ""

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze in [
                    Afleidingswijze.zaakobject,
                    Afleidingswijze.ander_datumkenmerk,
                ]:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.objecttype"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.required_code
                    )
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_registratie(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["registratie"] = "test"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.ander_datumkenmerk:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.registratie"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.empty_code
                    )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_registratie_empty(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["registratie"] = ""

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.ander_datumkenmerk:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.registratie"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.required_code
                    )
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_value_for_procestermijn(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["procestermijn"] = "P5M"

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.termijn:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()
                else:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.procestermijn"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.empty_code
                    )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_procestermijn_null(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        for afleidingswijze in Afleidingswijze.labels:
            with self.subTest(afleidingswijze=afleidingswijze):
                archiefprocedure = deepcopy(MAPPING[afleidingswijze])
                archiefprocedure["procestermijn"] = None

                data = {
                    "zaaktype": f"http://testserver{zaaktype_url}",
                    "omschrijving": "illum",
                    "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
                    "selectielijstklasse": self._get_selectielijstklasse_url(
                        afleidingswijze
                    ),
                    "archiefnominatie": "blijvend_bewaren",
                    "archiefactietermijn": "P10Y",
                    "brondatumArchiefprocedure": archiefprocedure,
                }

                with requests_mock.Mocker() as m:
                    m.register_uri(
                        "GET",
                        RESULTAATTYPEOMSCHRIJVING_URL,
                        json={"omschrijving": "test"},
                    )
                    with mock_client(self.RESPONSES):
                        response = self.client.post(self.list_url, data)

                if afleidingswijze == Afleidingswijze.termijn:
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

                    error = get_validation_errors(
                        response, "brondatumArchiefprocedure.procestermijn"
                    )
                    self.assertEqual(
                        error["code"], BrondatumArchiefprocedureValidator.required_code
                    )
                else:
                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    ResultaatType.objects.get().delete()

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_selectielijstklasse_bewaartermijn_empty_allowed(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=True
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})

        afleidingswijze = "afgehandeld"

        archiefprocedure = deepcopy(MAPPING[afleidingswijze])

        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": RESULTAATTYPEOMSCHRIJVING_URL,
            "selectielijstklasse": self._get_selectielijstklasse_url(afleidingswijze),
            "archiefnominatie": "blijvend_bewaren",
            "brondatumArchiefprocedure": archiefprocedure,
        }

        with requests_mock.Mocker() as m:
            m.register_uri(
                "GET",
                RESULTAATTYPEOMSCHRIJVING_URL,
                json={"omschrijving": "test"},
            )
            m.register_uri(
                "GET",
                SELECTIELIJSTKLASSE_PROCESTERMIJN_NIHIL_URL,
                json={"bewaartermijn": None},
            )
            with mock_client(self.RESPONSES):
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ResultaatTypeScopeTests(APITestCase, JWTAuthMixin):
    heeft_alle_autorisaties = False
    scopes = [SCOPE_CATALOGI_FORCED_WRITE]
    list_url = reverse_lazy(ResultaatType)

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_create_resultaattype_non_concept_zaaktype_forced(
        self, mock_shape, mock_fetch
    ):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse("zaaktype-detail", kwargs={"uuid": zaaktype.uuid})
        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "illum",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
            "besluittype_omschrijving": ["foobar", "foobar2"],
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resultaattype = ResultaatType.objects.get()
        self.assertEqual(resultaattype.omschrijving_generiek, "test")
        self.assertEqual(resultaattype.zaaktype, zaaktype)
        self.assertEqual(
            resultaattype.brondatum_archiefprocedure_afleidingswijze,
            Afleidingswijze.afgehandeld,
        )

    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    @patch("vng_api_common.oas.fetcher.fetch", return_value={})
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_update_resultaattype_non_concept_zaaktype(self, *mocks):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        zaaktype_url = reverse(zaaktype)
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        resultaattypeomschrijving_url = "http://example.com/omschrijving/1"
        data = {
            "zaaktype": f"http://testserver{zaaktype_url}",
            "omschrijving": "aangepast",
            "resultaattypeomschrijving": resultaattypeomschrijving_url,
            "selectielijstklasse": SELECTIELIJSTKLASSE_URL,
            "archiefnominatie": "blijvend_bewaren",
            "archiefactietermijn": "P10Y",
            "brondatumArchiefprocedure": {
                "afleidingswijze": Afleidingswijze.afgehandeld,
                "einddatumBekend": False,
                "procestermijn": None,
                "datumkenmerk": "",
                "objecttype": "",
                "registratie": "",
            },
        }

        responses = {
            SELECTIELIJSTKLASSE_URL: {
                "url": SELECTIELIJSTKLASSE_URL,
                "procesType": PROCESTYPE_URL,
                "procestermijn": Procestermijn.nihil,
            }
        }

        with mock_client(responses):
            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", resultaattypeomschrijving_url, json={"omschrijving": "test"}
                )
                response = self.client.put(resultaattype_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")

    def test_partial_update_resultaattype_non_concept_zaaktype(self):
        zaaktype = ZaakTypeFactory.create(
            selectielijst_procestype=PROCESTYPE_URL, concept=False
        )
        resultaattype = ResultaatTypeFactory.create(zaaktype=zaaktype)
        resultaattype_url = reverse(resultaattype)

        response = self.client.patch(resultaattype_url, {"omschrijving": "aangepast"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["omschrijving"], "aangepast")
