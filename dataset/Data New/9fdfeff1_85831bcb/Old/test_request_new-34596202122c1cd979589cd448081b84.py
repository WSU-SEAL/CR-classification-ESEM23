# Copyright 2013 Intel Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Tests for PCI request."""
from oslo_utils.fixture import uuidsentinel as uuids

from nova import exception
from nova.pci import request
from nova import test


_fake_alias1 = """{
               "name": "QuicAssist",
               "capability_type": "pci",
               "product_id": "4443",
               "vendor_id": "8086",
               "device_type": "type-PCI",
               "numa_policy": "legacy"
               }"""

_fake_alias11 = """{
               "name": "QuicAssist",
               "capability_type": "pci",
               "product_id": "4444",
               "vendor_id": "8086",
               "device_type": "type-PCI"
               }"""

_fake_alias2 = """{
               "name": "xxx",
               "capability_type": "pci",
               "product_id": "1111",
               "vendor_id": "1111",
               "device_type": "N"
               }"""

_fake_alias3 = """{
               "name": "IntelNIC",
               "capability_type": "pci",
               "product_id": "1111",
               "vendor_id": "8086",
               "device_type": "type-PF"
               }"""

_fake_alias4 = """{
               "name": " Cirrus Logic ",
               "capability_type": "pci",
               "product_id": "0ff2",
               "vendor_id": "10de",
               "device_type": "type-PCI"
               }"""


class AliasTestCase(test.NoDBTestCase):

    def test_valid_alias(self):
        self.flags(alias=[_fake_alias1], group='pci')
        result = request._get_alias_from_config()
        expected_result = (
            'legacy',
            [{
                "capability_type": "pci",
                "product_id": "4443",
                "vendor_id": "8086",
                "dev_type": "type-PCI",
            }])
        self.assertEqual(expected_result, result['QuicAssist'])

    def test_valid_multispec_alias(self):
        self.flags(alias=[_fake_alias1, _fake_alias11], group='pci')
        result = request._get_alias_from_config()
        expected_result = (
            'legacy',
            [{
                "capability_type": "pci",
                "product_id": "4443",
                "vendor_id": "8086",
                "dev_type": "type-PCI"
            }, {
                "capability_type": "pci",
                "product_id": "4444",
                "vendor_id": "8086",
                "dev_type": "type-PCI"
            }])
        self.assertEqual(expected_result, result['QuicAssist'])

    def test_invalid_type_alias(self):
        self.flags(alias=[_fake_alias2], group='pci')
        self.assertRaises(exception.PciInvalidAlias,
            request._get_alias_from_config)

    def test_invalid_product_id_alias(self):
        self.flags(alias=[
            """{
                "name": "xxx",
                "capability_type": "pci",
                "product_id": "g111",
                "vendor_id": "1111",
                "device_type": "NIC"
                }"""],
                   group='pci')
        self.assertRaises(exception.PciInvalidAlias,
            request._get_alias_from_config)

    def test_invalid_vendor_id_alias(self):
        self.flags(alias=[
            """{
                "name": "xxx",
                "capability_type": "pci",
                "product_id": "1111",
                "vendor_id": "0xg111",
                "device_type": "NIC"
                }"""],
                   group='pci')
        self.assertRaises(exception.PciInvalidAlias,
            request._get_alias_from_config)

    def test_invalid_cap_type_alias(self):
        self.flags(alias=[
            """{
                "name": "xxx",
                "capability_type": "usb",
                "product_id": "1111",
                "vendor_id": "8086",
                "device_type": "NIC"
                }"""],
                   group='pci')
        self.assertRaises(exception.PciInvalidAlias,
            request._get_alias_from_config)

    def test_invalid_numa_policy(self):
        self.flags(alias=[
            """{
                "name": "xxx",
                "capability_type": "pci",
                "product_id": "1111",
                "vendor_id": "8086",
                "device_type": "NIC",
                "numa_policy": "derp"
                }"""],
                   group='pci')
        self.assertRaises(exception.PciInvalidAlias,
            request._get_alias_from_config)

    def test_conflicting_device_type(self):
        """Check behavior when device_type conflicts occur."""
        self.flags(alias=[
            """{
                "name": "xxx",
                "capability_type": "pci",
                "product_id": "1111",
                "vendor_id": "8086",
                "device_type": "NIC"
                }""",
            """{
                "name": "xxx",
                "capability_type": "pci",
                "product_id": "1111",
                "vendor_id": "8086",
                "device_type": "type-PCI"
                }"""],
                   group='pci')
        self.assertRaises(
            exception.PciInvalidAlias,
            request._get_alias_from_config)

    def test_conflicting_numa_policy(self):
        """Check behavior when numa_policy conflicts occur."""
        self.flags(alias=[
            """{
                "name": "xxx",
                "capability_type": "pci",
                "product_id": "1111",
                "vendor_id": "8086",
                "numa_policy": "required",
                }""",
            """{
                "name": "xxx",
                "capability_type": "pci",
                "product_id": "1111",
                "vendor_id": "8086",
                "numa_policy": "legacy",
                }"""],
                   group='pci')
        self.assertRaises(
            exception.PciInvalidAlias,
            request._get_alias_from_config)

    def _verify_result(self, expected, real):
        exp_real = zip(expected, real)
        for exp, real in exp_real:
            self.assertEqual(exp['count'], real.count)
            self.assertEqual(exp['alias_name'], real.alias_name)
            self.assertEqual(exp['spec'], real.spec)

    def test_alias_2_request(self):
        self.flags(alias=[_fake_alias1, _fake_alias3], group='pci')
        expect_request = [
            {'count': 3,
             'requester_id': uuids.flavor_id,
             'spec': [{'vendor_id': '8086', 'product_id': '4443',
                       'dev_type': 'type-PCI',
                       'capability_type': 'pci'}],
                       'alias_name': 'QuicAssist'},

            {'count': 1,
             'requester_id': uuids.flavor_id,
             'spec': [{'vendor_id': '8086', 'product_id': '1111',
                       'dev_type': "type-PF",
                       'capability_type': 'pci'}],
             'alias_name': 'IntelNIC'}, ]

        requests = request._translate_alias_to_requests(
            "QuicAssist : 3, IntelNIC: 1", uuids.flavor_id)
        self.assertEqual(set([p['count'] for p in requests]), set([1, 3]))
        self._verify_result(expect_request, requests)

    def test_alias_2_request_invalid(self):
        self.flags(alias=[_fake_alias1, _fake_alias3], group='pci')
        self.assertRaises(exception.PciRequestAliasNotDefined,
                          request._translate_alias_to_requests,
                          "QuicAssistX : 3", uuids.flavor_id)

    def test_get_pci_requests_from_flavor(self):
        self.flags(alias=[_fake_alias1, _fake_alias3], group='pci')
        expect_request = [
            {'count': 3,
             'spec': [{'vendor_id': '8086', 'product_id': '4443',
                       'dev_type': "type-PCI",
                       'capability_type': 'pci'}],
             'alias_name': 'QuicAssist'},

            {'count': 1,
             'spec': [{'vendor_id': '8086', 'product_id': '1111',
                       'dev_type': "type-PF",
                       'capability_type': 'pci'}],
             'alias_name': 'IntelNIC'}, ]

        flavor = {'extra_specs': {"pci_passthrough:alias":
                                  "QuicAssist:3, IntelNIC: 1"},
                  'id': uuids.flavor_id}
        requests = request.get_pci_requests_from_flavor(flavor)
        self.assertEqual(set([1, 3]),
                         set([p.count for p in requests.requests]))
        self._verify_result(expect_request, requests.requests)

    def test_get_pci_requests_from_flavor_including_space(self):
        self.flags(alias=[_fake_alias3, _fake_alias4], group='pci')
        expect_request = [
            {'count': 4,
             'spec': [{'vendor_id': '10de', 'product_id': '0ff2',
                       'dev_type': "type-PCI",
                       'capability_type': 'pci'}],
             'alias_name': 'Cirrus Logic'},

            {'count': 3,
             'spec': [{'vendor_id': '8086', 'product_id': '1111',
                       'dev_type': "type-PF",
                       'capability_type': 'pci'}],
             'alias_name': 'IntelNIC'}, ]

        flavor = {'extra_specs': {"pci_passthrough:alias":
                                  " Cirrus Logic : 4, IntelNIC: 3"},
                  'id': uuids.flavor_id}
        requests = request.get_pci_requests_from_flavor(flavor)
        self.assertEqual(set([3, 4]),
                         set([p.count for p in requests.requests]))
        self._verify_result(expect_request, requests.requests)

    def test_get_pci_requests_from_flavor_no_extra_spec(self):
        self.flags(alias=[_fake_alias1, _fake_alias3], group='pci')
        flavor = {}
        requests = request.get_pci_requests_from_flavor(flavor)
        self.assertEqual([], requests.requests)
