# Copyright 2019 OpenStack Foundation
# Copyright 2019 Aptira Pty Ltd
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

import binascii
import ddt
import mock
import os
import six

import nova.privsep.libvirt
from nova import test
from nova.tests import fixtures
from oslo_utils import units


class LibvirtTestCase(test.NoDBTestCase):
    """Test libvirt related utility methods."""

    def setUp(self):
        super(LibvirtTestCase, self).setUp()
        self.useFixture(fixtures.PrivsepFixture())

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_dmcrypt_create_volume(self, mock_execute):
        nova.privsep.libvirt.dmcrypt_create_volume(
            '/fake/path', '/dev/nosuch', 'LUKS1', 1024, 'I am a fish')
        mock_execute.assert_called_with(
            'cryptsetup', 'create', '/fake/path', '/dev/nosuch',
           '--cipher=LUKS1', '--key-size=1024', '--key-file=-',
            process_input=binascii.hexlify('I am a fish').decode('utf-8'))

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_dmcrypt_delete_volume(self, mock_execute):
        nova.privsep.libvirt.dmcrypt_delete_volume('/fake/path')
        mock_execute.assert_called_with('cryptsetup', 'remove', '/fake/path')

    @mock.patch('oslo_concurrency.processutils.execute')
    @mock.patch('os.stat')
    @mock.patch('os.chmod')
    def test_ploop_init(self, mock_chmod, mock_stat, mock_execute):
        nova.privsep.libvirt.ploop_init(1024, 'raw', 'ext4', '/fake/path')
        mock_execute.assert_called_with(
            'ploop', 'init', '-s', 1024, '-f', 'raw', '-t',
            'ext4', '/fake/path', check_exit_code=True)
        mock_stat.assert_called_with('/fake/path')
        mock_chmod.asert_called_with('/fake/path', mock.ANY)

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_ploop_resize(self, mock_execute):
        nova.privsep.libvirt.ploop_resize(
            '/fake/path', 2048 * units.Mi)
        mock_execute.assert_called_with('prl_disk_tool', 'resize',
                                        '--size', '2048M',
                                        '--resize_partition',
                                        '--hdd', '/fake/path',
                                        check_exit_code=True)

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_ploop_restore_descriptor(self, mock_execute):
        nova.privsep.libvirt.ploop_restore_descriptor(
            '/img/dir', 'imagefile', 'raw')
        mock_execute.assert_called_with(
            'ploop', 'restore-descriptor', '-f', 'raw',
            '/img/dir', 'imagefile', check_exit_code=True)

    def test_enable_hairping(self):
        mock_open = mock.mock_open()
        with mock.patch.object(six.moves.builtins, 'open',
                               new=mock_open) as mock_open:
            nova.privsep.libvirt.enable_hairpin('eth0')

            handle = mock_open()
            self.assertTrue(mock.call('/sys/class/net/eth0/brport/'
                                      'hairpin_mode', 'w') in
                            mock_open.mock_calls)
            handle.write.assert_called_with('1')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_plug_infiniband_vif(self, mock_execute):
        nova.privsep.libvirt.plug_infiniband_vif('fakemac', 'devid', 'fabric',
                                                 'netmodel', 'pcislot')
        mock_execute.assert_called_with(
            'ebrctl', 'add-port', 'fakemac', 'devid', 'fabric', 'netmodel',
            'pcislot')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_unplug_infiniband_vif(self, mock_execute):
        nova.privsep.libvirt.unplug_infiniband_vif('fabric', 'fakemac')
        mock_execute.assert_called_with(
            'ebrctl', 'del-port', 'fabric', 'fakemac')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_plug_midonet_vif(self, mock_execute):
        nova.privsep.libvirt.plug_midonet_vif('portid', 'dev')
        mock_execute.assert_called_with(
            'mm-ctl', '--bind-port', 'portid', 'dev')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_unplug_midonet_vif(self, mock_execute):
        nova.privsep.libvirt.unplug_midonet_vif('portid')
        mock_execute.assert_called_with(
            'mm-ctl', '--unbind-port', 'portid')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_plug_plumgrid_vif(self, mock_execute):
        nova.privsep.libvirt.plug_plumgrid_vif(
            'dev', 'iface', 'addr', 'netid', 'tenantid')
        mock_execute.assert_has_calls(
            [
                mock.call('ifc_ctl', 'gateway', 'add_port', 'dev'),
                mock.call('ifc_ctl', 'gateway', 'ifup', 'dev',
                          'access_vm', 'iface', 'addr',
                          'pgtag2=netid', 'pgtag1=tenantid')
            ])

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_unplug_plumgrid_vif(self, mock_execute):
        nova.privsep.libvirt.unplug_plumgrid_vif('dev')
        mock_execute.assert_has_calls(
            [
                mock.call('ifc_ctl', 'gateway', 'ifdown', 'dev'),
                mock.call('ifc_ctl', 'gateway', 'del_port', 'dev')
            ])

    @mock.patch('fcntl.fcntl', return_value=32769)
    def test_readpty(self, mock_fcntl):
        mock_open = mock.mock_open()
        with test.nested(
                mock.patch.object(six.moves.builtins, 'open', new=mock_open),
                mock.patch.object(six.moves.builtins, '__import__'),
                ) as (mock_open, mock_import):
            nova.privsep.libvirt.readpty('/fake/path')

            mock_import.assert_called()

            # NOTE(mikal): we can't assert that values from fcntl are passed
            # here because we can't import fcntl in these tests because it
            # is not present on Microsoft Windows.
            mock_fcntl.asert_has_calls(
                mock.call(mock.ANY, mock.ANY),
                mock.call(mock.ANY, mock.ANY, 32769 | os.O_NONBLOCK))
            self.assertTrue(mock.call('/fake/path', 'r') in
                            mock_open.mock_calls)

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_xend_probe(self, mock_execute):
        nova.privsep.libvirt.xend_probe()
        mock_execute.assert_called_with('xend', 'status',
                                        check_exit_code=True)

    def test_create_nmdev(self):
        mock_open = mock.mock_open()
        with mock.patch.object(six.moves.builtins, 'open',
                               new=mock_open) as mock_open:
            nova.privsep.libvirt.create_mdev('phys', 'mdevtype',
                                             uuid='fakeuuid')

            handle = mock_open()
            self.assertTrue(mock.call('/sys/class/mdev_bus/phys/'
                                      'mdev_supported_types/mdevtype/create',
                                      'w') in mock_open.mock_calls)
            handle.write.assert_called_with('fakeuuid')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_umount(self, mock_execute):
        nova.privsep.libvirt.umount('/fake/path')
        mock_execute.assert_called_with('umount', '/fake/path')

    @mock.patch('oslo_concurrency.processutils.execute')
    def test_unprivileged_umount(self, mock_execute):
        nova.privsep.libvirt.unprivileged_umount('/fake/path')
        mock_execute.assert_called_with('umount', '/fake/path')


@ddt.ddt
class PrivsepLibvirtMountTestCase(test.NoDBTestCase):

    QB_BINARY = "mount.quobyte"
    QB_FIXED_OPT_1 = "--disable-xattrs"
    FAKE_VOLUME = "fake_volume"
    FAKE_MOUNT_BASE = "/fake/mount/base"

    def setUp(self):
        super(PrivsepLibvirtMountTestCase, self).setUp()
        self.useFixture(test.nova_fixtures.PrivsepFixture())

    @ddt.data(None, "/FAKE/CFG/PATH.cfg")
    @mock.patch('oslo_concurrency.processutils.execute')
    def test_systemd_run_qb_mount(self, cfg_file, mock_execute):
        sysd_bin = "systemd-run"
        sysd_opt_1 = "--scope"

        nova.privsep.libvirt.systemd_run_qb_mount(
            self.FAKE_VOLUME, self.FAKE_MOUNT_BASE, cfg_file=cfg_file)

        if cfg_file:
            mock_execute.assert_called_once_with(sysd_bin, sysd_opt_1,
                                                 self.QB_BINARY,
                                                 self.QB_FIXED_OPT_1,
                                                 self.FAKE_VOLUME,
                                                 self.FAKE_MOUNT_BASE,
                                                 "-c",
                                                 cfg_file)
        else:
            mock_execute.assert_called_once_with(sysd_bin, sysd_opt_1,
                                                 self.QB_BINARY,
                                                 self.QB_FIXED_OPT_1,
                                                 self.FAKE_VOLUME,
                                                 self.FAKE_MOUNT_BASE)

    @ddt.data(None, "/FAKE/CFG/PATH.cfg")
    @mock.patch('oslo_concurrency.processutils.execute')
    def test_unprivileged_qb_mount(self, cfg_file, mock_execute):

        nova.privsep.libvirt.unprivileged_qb_mount(self.FAKE_VOLUME,
                                                   self.FAKE_MOUNT_BASE,
                                                   cfg_file=cfg_file)

        if cfg_file:
            mock_execute.assert_called_once_with(self.QB_BINARY,
                                                 self.QB_FIXED_OPT_1,
                                                 self.FAKE_VOLUME,
                                                 self.FAKE_MOUNT_BASE,
                                                 "-c",
                                                 cfg_file)
        else:
            mock_execute.assert_called_once_with(self.QB_BINARY,
                                                 self.QB_FIXED_OPT_1,
                                                 self.FAKE_VOLUME,
                                                 self.FAKE_MOUNT_BASE)
