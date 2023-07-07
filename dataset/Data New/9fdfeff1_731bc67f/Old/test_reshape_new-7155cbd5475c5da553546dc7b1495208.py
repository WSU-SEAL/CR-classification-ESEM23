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
import time

import mock
from oslo_config import cfg
from oslo_log import log as logging

from nova.tests.functional.libvirt import base
from nova.tests.unit.virt.libvirt import fakelibvirt

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class VGPUReshapeTests(base.ServersTestBase):
    # the minimum libvirt version needed for vgpu
    MIN_LIBVIRT_MDEV_SUPPORT = 3004000

    def _wait_for_state_change(self, server, expected_status):
        for i in range(0, 50):
            server = self.api.get_server(server['id'])
            if server['status'] == expected_status:
                return server
            time.sleep(.1)
        self.assertEqual(expected_status, server['status'])
        return server

    def test_create_server_with_vgpu(self):
        """Verify that vgpu rehape works with libvirt driver

        1) create a server with an old tree where ther VGPU resource is on the
           compute provider
        2) trigger a reshape
        3) check that the allocation of the server is still valid
        4) create another server now against the new tree
        """

        # NOTE(gibi): We cannot simply ask the virt driver to create an old
        # RP tree with vgpu on the root RP as that code path does not exists
        # any more. So we have to hack a "bit". We will create a compute
        # service without vgpu support to have the compute RP ready then we
        # manually add the VGPU resource to that RP in placement. Also we make
        # sure that during the instance claim the virt drive does not detect
        # the old tree as that would be a bad time for reshape. Later when the
        # compute service is restarted the driver will do the reshape.

        fake_connection = self._get_connection(
            host_info=fakelibvirt.HostInfo(),
            libvirt_version=self.MIN_LIBVIRT_MDEV_SUPPORT,
            mdev_info=fakelibvirt.HostMdevDevicesInfo())
        self.mock_conn.return_value = fake_connection

        # start a compute with vgpu support disabled so the driver will
        # ignore the content of the above HostMdevDeviceInfo
        self.flags(enabled_vgpu_types='', group='devices')
        self.compute = self.start_service('compute')

        # create the VGPU resource in placement manually
        compute_rp_uuid = self.placement_api.get(
            '/resource_providers?name=compute1').body[
            'resource_providers'][0]['uuid']
        inventories = self.placement_api.get(
            '/resource_providers/%s/inventories' % compute_rp_uuid).body
        inventories['inventories']['VGPU'] = {
            'allocation_ratio': 1.0,
            'max_unit': 2,
            'min_unit': 1,
            'reserved': 0,
            'step_size': 1,
            'total': 2}
        self.placement_api.put(
            '/resource_providers/%s/inventories' % compute_rp_uuid,
            inventories)

        # now we boot a server with vgpu
        extra_spec = {"resources:VGPU": 1}
        flavor_id = self._create_flavor(extra_spec=extra_spec)

        server_req = self._build_server(flavor_id)

        # NOTE(gibi): during instance_claim() there is a
        # driver.update_provider_tree() call that would detect the old tree and
        # would fail as this is not a good time to reshape. To avoid that we
        # temporarly mock update_provider_tree here.
        with mock.patch('nova.virt.libvirt.driver.LibvirtDriver.'
                        'update_provider_tree'):
            created_server = self.api.post_server({'server': server_req})
            server1 = self._wait_for_state_change(created_server, 'ACTIVE')

        # verify that the inventory, usages and allocation are correct before
        # the reshape
        compute_inventory = self.placement_api.get(
            '/resource_providers/%s/inventories' % compute_rp_uuid).body[
            'inventories']
        self.assertEqual(2, compute_inventory['VGPU']['total'])
        compute_usages = self.placement_api.get(
            '/resource_providers/%s/usages' % compute_rp_uuid).body[
            'usages']
        self.assertEqual(1, compute_usages['VGPU'])
        allocations = self.placement_api.get(
            '/allocations/%s' % server1['id']).body[
            'allocations']
        self.assertEqual(
            {'DISK_GB': 20, 'MEMORY_MB': 2048, 'VCPU': 2, 'VGPU': 1},
            allocations[compute_rp_uuid]['resources'])

        # enabled vgpu support
        self.flags(enabled_vgpu_types='nvidia-11', group='devices')
        # restart compute which will trigger a reshape
        self.restart_compute_service(self.compute)

        # verify that the inventory, usages and allocation are correct after
        # the reshape
        compute_inventory = self.placement_api.get(
            '/resource_providers/%s/inventories' % compute_rp_uuid).body[
            'inventories']
        self.assertNotIn('VGPU', compute_inventory)

        gpu_rp_uuid = self.placement_api.get(
            '/resource_providers?name=compute1_pci_0000_06_00_0').body[
            'resource_providers'][0]['uuid']

        gpu_inventory = self.placement_api.get(
            '/resource_providers/%s/inventories' % gpu_rp_uuid).body[
            'inventories']
        self.assertEqual(2, gpu_inventory['VGPU']['total'])

        gpu_usages = self.placement_api.get(
            '/resource_providers/%s/usages' % gpu_rp_uuid).body[
            'usages']
        self.assertEqual(1, gpu_usages['VGPU'])

        allocations = self.placement_api.get(
            '/allocations/%s' % server1['id']).body[
            'allocations']
        self.assertEqual(
            {'DISK_GB': 20, 'MEMORY_MB': 2048, 'VCPU': 2},
            allocations[compute_rp_uuid]['resources'])
        self.assertEqual(
            {'VGPU': 1},
            allocations[gpu_rp_uuid]['resources'])

        # now create one more instance with vgpu against the reshaped tree
        created_server = self.api.post_server({'server': server_req})
        server2 = self._wait_for_state_change(created_server, 'ACTIVE')

        gpu_usages = self.placement_api.get(
            '/resource_providers/%s/usages' % gpu_rp_uuid).body[
            'usages']
        self.assertEqual(2, gpu_usages['VGPU'])

        allocations = self.placement_api.get(
            '/allocations/%s' % server2['id']).body[
            'allocations']
        self.assertEqual(
            {'DISK_GB': 20, 'MEMORY_MB': 2048, 'VCPU': 2},
            allocations[compute_rp_uuid]['resources'])
        self.assertEqual(
            {'VGPU': 1},
            allocations[gpu_rp_uuid]['resources'])
