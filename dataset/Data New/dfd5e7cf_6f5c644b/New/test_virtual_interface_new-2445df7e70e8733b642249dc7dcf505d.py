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

import datetime
from oslo_config import cfg

from nova import context
from nova import exception
from nova import objects
from nova.objects import virtual_interface
from nova.tests.functional import integrated_helpers
from nova.tests.unit import fake_network

CONF = cfg.CONF


def _delete_vif_list(context, instance_uuid):
    vif_list = objects.VirtualInterfaceList.\
        get_by_instance_uuid(context, instance_uuid)

    # Set old VirtualInterfaces as deleted.
    for vif in vif_list:
        vif.destroy()


def _verify_list_fulfillment(context, instance_uuid):
    try:
        info_cache = objects.InstanceInfoCache.\
            get_by_instance_uuid(context, instance_uuid)
    except exception.InstanceInfoCacheNotFound:
        info_cache = []

    vif_list = objects.VirtualInterfaceList.\
        get_by_instance_uuid(context, instance_uuid)
    vif_list = filter(lambda x: not x.deleted,
                      vif_list)

    cached_vif_ids = [vif['id'] for vif in info_cache.network_info]
    db_vif_ids = [vif.uuid for vif in vif_list]
    return cached_vif_ids == db_vif_ids


class VirtualInterfaceListMigrationTestCase(
    integrated_helpers._IntegratedTestBase,
    integrated_helpers.InstanceHelperMixin):

    ADMIN_API = True
    USE_NEUTRON = True
    api_major_version = 'v2.1'
    _image_ref_parameter = 'imageRef'
    _flavor_ref_parameter = 'flavorRef'

    def setUp(self):
        super(VirtualInterfaceListMigrationTestCase, self).setUp()

        self.context = context.get_admin_context()
        fake_network.set_stub_network_methods(self)

    def _create_instances(self, pre_newton=2, total=5):
        request = self._build_minimal_create_server_request()
        request.update({'max_count': total})
        self.api.post_server({'server': request})

        self.instances = objects.InstanceList.get_all(self.context)
        # Make sure that we have all the needed instances
        self.assertEqual(total, len(self.instances))
        for instance in self.instances:
            self._wait_for_state_change(
                self.api, {'id': instance.uuid}, 'ACTIVE')

        # Attach fake interfaces to instances
        network_id = list(self.neutron._networks.keys())[0]
        for i in range(0, total):
            for k in range(0, 4):
                self.api.attach_interface(self.instances[i].uuid,
                    {"interfaceAttachment": {"net_id": network_id}})

        # Fake the pre-newton behaviour by removing the
        # VirtualInterfacesList objects.
        if pre_newton:
            for i in range(0, pre_newton):
                _delete_vif_list(self.context, self.instances[i].uuid)

    def test_migration_nothing_to_migrate(self):
        """This test when there already populated VirtualInterfaceList
           objects for created instances.
        """
        self._create_instances(pre_newton=0, total=5)
        match, done = virtual_interface.fill_virtual_interface_list(
            self.context, 5)

        self.assertEqual(0, match)
        self.assertEqual(0, done)

    def test_migration_pre_newton_instances(self):
        """This test when there is an instance created in release
           older than Newton. For those instances the VirtualInterfaceList
           needs to be re-created from cache.
        """
        # Lets spawn 3 pre-newton instances and 2 new ones
        self._create_instances(pre_newton=3, total=5)
        match, done = virtual_interface.fill_virtual_interface_list(
            self.context, 5)

        self.assertEqual(3, match)
        self.assertEqual(3, done)

        # Make sure we ran over all the instances - verify if marker works
        match, done = virtual_interface.fill_virtual_interface_list(
            self.context, 50)
        self.assertEqual(0, match)
        self.assertEqual(0, done)

        for i in range(0, 5):
            _verify_list_fulfillment(self.context, self.instances[i].uuid)

    def test_migration_pre_newton_instance_new_vifs(self):
        """This test when instance was created before Newton
           but in meantime new interfaces where attached and
           VirtualInterfaceList is not populated.
        """
        self._create_instances(pre_newton=0, total=1)

        vif_list = objects.VirtualInterfaceList.get_by_instance_uuid(
            self.context, self.instances[0].uuid)
        # Drop first vif from list to pretend old instance
        vif_list[0].destroy()

        match, done = virtual_interface.fill_virtual_interface_list(
            self.context, 5)

        # The whole VirtualInterfaceList should be rewritten and base
        # on cache.
        self.assertEqual(1, match)
        self.assertEqual(1, done)

        _verify_list_fulfillment(self.context, self.instances[0].uuid)

    def test_migration_attach_in_progress(self):
        """This test when number of vifs (db) is bigger than
           number taken from network cache. Potential
           port-attach is taking place.
        """
        self._create_instances(pre_newton=0, total=1)
        instance_info_cache = objects.InstanceInfoCache.get_by_instance_uuid(
            self.context, self.instances[0].uuid)

        # Delete last interface to pretend that's still in progress
        instance_info_cache.network_info.pop()
        instance_info_cache.updated_at = datetime.datetime(2015, 1, 1)

        instance_info_cache.save()

        match, done = virtual_interface.fill_virtual_interface_list(
            self.context, 5)

        # I don't know whats going on so instance VirtualInterfaceList
        # should stay untouched.
        self.assertEqual(0, match)
        self.assertEqual(0, done)

    def test_migration_empty_network_info(self):
        """This test if migration is not executed while
           NetworkInfo is empty, like instance without
           interfaces attached.
        """
        self._create_instances(pre_newton=0, total=1)
        instance_info_cache = objects.InstanceInfoCache.get_by_instance_uuid(
            self.context, self.instances[0].uuid)

        # Clean NetworkInfo. Pretend instance without interfaces.
        instance_info_cache.network_info = None
        instance_info_cache.save()

        match, done = virtual_interface.fill_virtual_interface_list(
            self.context, 5)

        self.assertEqual(0, match)
        self.assertEqual(0, done)

    def test_migration_inconsistent_data(self):
        """This test when vif (db) are in completely different
           comparing to network cache and we don't know how to
           deal with it. It's the corner-case.
        """
        self._create_instances(pre_newton=0, total=1)
        instance_info_cache = objects.InstanceInfoCache.get_by_instance_uuid(
            self.context, self.instances[0].uuid)

        # Change order of interfaces in NetworkInfo to fake
        # inconsistency between cache and db.
        nwinfo = instance_info_cache.network_info
        interface = nwinfo.pop()
        nwinfo.insert(0, interface)
        instance_info_cache.updated_at = datetime.datetime(2015, 1, 1)
        instance_info_cache.network_info = nwinfo

        # Update the cache
        instance_info_cache.save()

        match, done = virtual_interface.fill_virtual_interface_list(
            self.context, 5)

        # Cache is corrupted, so must be rewrited
        self.assertEqual(1, match)
        self.assertEqual(1, done)
