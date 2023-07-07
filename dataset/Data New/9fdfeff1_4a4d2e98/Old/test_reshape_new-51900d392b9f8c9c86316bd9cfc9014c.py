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

    def test_create_servers_with_vgpu(self):
        """Verify that vgpu reshape works with libvirt driver

        1) create two servers with an old tree where the VGPU resource is on
           the compute provider
        2) trigger a reshape
        3) check that the allocations of the servers are still valid
        4) create another server now against the new tree
        """

        # NOTE(gibi): We cannot simply ask the virt driver to create an old
        # RP tree with vgpu on the root RP as that code path does not exist
        # any more. So we have to hack a "bit". We will create a compute
        # service without vgpu support to have the compute RP ready then we
        # manually add the VGPU resources to that RP in placement. Also we make
        # sure that during the instance claim the virt driver does not detect
        # the old tree as that would be a bad time for reshape. Later when the
        # compute service is restarted the driver will do the reshape.

        fake_connection = self._get_connection(
            # We need more RAM or the 3rd server won't be created
            host_info=fakelibvirt.HostInfo(kB_mem=8192),
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
            'max_unit': 3,
            'min_unit': 1,
            'reserved': 0,
            'step_size': 1,
            'total': 3}
        self.placement_api.put(
            '/resource_providers/%s/inventories' % compute_rp_uuid,
            inventories)

        # now we boot two servers with vgpu
        extra_spec = {"resources:VGPU": 1}
        flavor_id = self._create_flavor(extra_spec=extra_spec)

        server_req = self._build_server(flavor_id)

        # NOTE(gibi): during instance_claim() there is a
        # driver.update_provider_tree() call that would detect the old tree and
        # would fail as this is not a good time to reshape. To avoid that we
        # temporarly mock update_provider_tree here.
        with mock.patch('nova.virt.libvirt.driver.LibvirtDriver.'
                        'update_provider_tree'):
            created_server1 = self.api.post_server({'server': server_req})
            server1 = self._wait_for_state_change(created_server1, 'ACTIVE')
            created_server2 = self.api.post_server({'server': server_req})
            server2 = self._wait_for_state_change(created_server2, 'ACTIVE')

        # verify that the inventory, usages and allocation are correct before
        # the reshape
        compute_inventory = self.placement_api.get(
            '/resource_providers/%s/inventories' % compute_rp_uuid).body[
            'inventories']
        self.assertEqual(3, compute_inventory['VGPU']['total'])
        compute_usages = self.placement_api.get(
            '/resource_providers/%s/usages' % compute_rp_uuid).body[
            'usages']
        self.assertEqual(2, compute_usages['VGPU'])
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

        # NOTE(sbauza): The two instances will use two different pGPUs
        # That said, we need to check all the pGPU inventories for knowing
        # which ones are used.
        usages = {}
        for pci_device in ['pci_0000_06_00_0', 'pci_0000_07_00_0',
                           'pci_0000_08_00_0']:
            gpu_rp_uuid = self.placement_api.get(
                '/resource_providers?name=compute1_%s' % pci_device).body[
                'resource_providers'][0]['uuid']
            gpu_inventory = self.placement_api.get(
                '/resource_providers/%s/inventories' % gpu_rp_uuid).body[
                'inventories']
            self.assertEqual(1, gpu_inventory['VGPU']['total'])

            gpu_usages = self.placement_api.get(
                '/resource_providers/%s/usages' % gpu_rp_uuid).body[
                'usages']
            usages[pci_device] = gpu_usages['VGPU']
        # Make sure that both instances are using different pGPUs
        used_devices = [dev for dev, usage in usages.items() if usage == 1]
        avail_devices = list(set(usages.keys()) - set(used_devices))
        self.assertEqual(2, len(used_devices))

        for server in [server1, server2]:
            allocations = self.placement_api.get(
                '/allocations/%s' % server['id']).body[
                'allocations']
            self.assertEqual(
                {'DISK_GB': 20, 'MEMORY_MB': 2048, 'VCPU': 2},
                allocations[compute_rp_uuid]['resources'])
            rp_uuids = list(allocations.keys())
            # We only have two RPs, the root and the child pGPU RP
            gpu_rp_uuid = (rp_uuids[1] if rp_uuids[0] == compute_rp_uuid
                           else rp_uuids[0])
            self.assertEqual(
                {'VGPU': 1},
                allocations[gpu_rp_uuid]['resources'])

        # now create one more instance with vgpu against the reshaped tree
        created_server = self.api.post_server({'server': server_req})
        server3 = self._wait_for_state_change(created_server, 'ACTIVE')

        # find the pGPU that wasn't used before we created the third instance
        # It should have taken the previously available pGPU
        device = avail_devices[0]
        gpu_rp_uuid = self.placement_api.get(
            '/resource_providers?name=compute1_%s' % device).body[
            'resource_providers'][0]['uuid']
        gpu_usages = self.placement_api.get(
            '/resource_providers/%s/usages' % gpu_rp_uuid).body[
            'usages']
        self.assertEqual(1, gpu_usages['VGPU'])

        allocations = self.placement_api.get(
            '/allocations/%s' % server3['id']).body[
            'allocations']
        self.assertEqual(
            {'DISK_GB': 20, 'MEMORY_MB': 2048, 'VCPU': 2},
            allocations[compute_rp_uuid]['resources'])
        self.assertEqual(
            {'VGPU': 1},
            allocations[gpu_rp_uuid]['resources'])
