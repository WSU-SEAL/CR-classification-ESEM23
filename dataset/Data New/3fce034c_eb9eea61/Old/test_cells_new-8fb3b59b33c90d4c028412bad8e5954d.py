# Copyright 2012 Nebula, Inc.
# Copyright 2013 IBM Corp.
# Copyright 2019 Red Hat, Inc.
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

from nova.tests.functional.api import client as api_client
from nova.tests.functional.api_sample_tests import api_sample_base


class CellsTest(api_sample_base.ApiSampleTestBaseV21):

    def test_cells_list(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_get, 'os-cells')
        self.assertEqual(410, ex.response.status_code)

    def test_cells_capacity(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_get, 'os-cells/capacities')
        self.assertEqual(410, ex.response.status_code)

    def test_cells_detail(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_get, 'os-cells/detail')
        self.assertEqual(410, ex.response.status_code)

    def test_cells_info(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_get, 'os-cells/info')
        self.assertEqual(410, ex.response.status_code)

    def test_cells_sync_instances(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_post, 'os-cells/sync_instances',
                               {})
        self.assertEqual(410, ex.response.status_code)

    def test_cell_create(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_post, 'os-cells', {})
        self.assertEqual(410, ex.response.status_code)

    def test_cell_show(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_get, 'os-cells/cell3')
        self.assertEqual(410, ex.response.status_code)

    def test_cell_update(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_put, 'os-cells/cell3', {})
        self.assertEqual(410, ex.response.status_code)

    def test_cell_delete(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_delete, 'os-cells/cell3')
        self.assertEqual(410, ex.response.status_code)

    def test_cell_capacity(self):
        ex = self.assertRaises(api_client.OpenStackApiException,
                               self.api.api_get, 'os-cells/cell3/capacities')
        self.assertEqual(410, ex.response.status_code)
