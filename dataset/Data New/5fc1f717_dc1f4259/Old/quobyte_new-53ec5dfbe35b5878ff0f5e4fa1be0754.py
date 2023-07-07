# Copyright (c) 2015 Quobyte Inc.
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

import errno
import os

from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_utils import fileutils
import psutil
import six

import nova.conf
from nova import exception as nova_exception
from nova.i18n import _
from nova.privsep import libvirt
from nova import utils
from nova.virt.libvirt import utils as libvirt_utils
from nova.virt.libvirt.volume import fs

LOG = logging.getLogger(__name__)

CONF = nova.conf.CONF

SOURCE_PROTOCOL = 'quobyte'
SOURCE_TYPE = 'file'
DRIVER_CACHE = 'none'
DRIVER_IO = 'native'
VALID_SYSD_STATES = ["starting", "running", "degraded"]
SYSTEMCTL_CHECK_PATH = "/run/systemd/system"


_is_systemd = None


@utils.synchronized('qb_is_systemd')
def is_systemd():
    """Checks if the host is running systemd"""
    global _is_systemd

    if _is_systemd is not None:
        return _is_systemd

    _is_systemd = False

    if psutil.Process(1).name() == "systemd" or os.path.exists(
            SYSTEMCTL_CHECK_PATH):
        # NOTE(kaisers): exit code might be >1 in theory but in practice this
        # is hard coded to 1. Due to backwards compatibility and systemd
        # CODING_STYLE this is unlikely to change.
        sysdout, sysderr = processutils.execute("systemctl",
                                                "is-system-running",
                                                check_exit_code=[0, 1])
        for state in VALID_SYSD_STATES:
            if state == sysdout.strip():
                _is_systemd = True
                break

    return _is_systemd


def mount_volume(volume, mnt_base, configfile=None):
    """Wraps execute calls for mounting a Quobyte volume"""
    fileutils.ensure_tree(mnt_base)

    # Note(kaisers): with systemd this requires a separate CGROUP to
    # prevent Nova service stop/restarts from killing the mount.
    if is_systemd():
        LOG.debug('Mounting volume %s at mount point %s via systemd-run',
                  volume, mnt_base)
        libvirt.systemd_run_qb_mount(volume, mnt_base, cfg_file=configfile)
    else:
        LOG.debug('Mounting volume %s at mount point %s via mount.quobyte',
                  volume, mnt_base, cfg_file=configfile)

        libvirt.unprivileged_qb_mount(volume, mnt_base, cfg_file=configfile)
    LOG.info('Mounted volume: %s', volume)


def umount_volume(mnt_base):
    """Wraps execute calls for unmouting a Quobyte volume"""
    try:
        if is_systemd():
            libvirt.umount(mnt_base)
        else:
            libvirt.unprivileged_umount(mnt_base)
    except processutils.ProcessExecutionError as exc:
        if 'Device or resource busy' in six.text_type(exc):
            LOG.error("The Quobyte volume at %s is still in use.", mnt_base)
        else:
            LOG.exception(_("Couldn't unmount the Quobyte Volume at %s"),
                          mnt_base)


def validate_volume(mount_path):
    """Runs a number of tests to be sure this is a (working) Quobyte mount"""
    partitions = psutil.disk_partitions(all=True)
    for p in partitions:
        if mount_path != p.mountpoint:
            continue
        if p.device.startswith("quobyte@"):
            statresult = os.stat(mount_path)
            # Note(kaisers): Quobyte always shows mount points with size 0
            if statresult.st_size == 0:
                # client looks healthy
                return  # we're happy here
            else:
                msg = (_("The mount %(mount_path)s is not a "
                         "valid Quobyte volume. Stale mount?")
                       % {'mount_path': mount_path})
            raise nova_exception.InvalidVolume(msg)
        else:
            msg = (_("The mount %(mount_path)s is not a valid"
                     " Quobyte volume according to partition list.")
                   % {'mount_path': mount_path})
            raise nova_exception.InvalidVolume(msg)
    msg = (_("No matching Quobyte mount entry for %(mount_path)s"
             " could be found for validation in partition list.")
           % {'mount_path': mount_path})
    raise nova_exception.InvalidVolume(msg)


class LibvirtQuobyteVolumeDriver(fs.LibvirtBaseFileSystemVolumeDriver):
    """Class implements libvirt part of volume driver for Quobyte."""

    def _get_mount_point_base(self):
        return CONF.libvirt.quobyte_mount_point_base

    def get_config(self, connection_info, disk_info):
        conf = super(LibvirtQuobyteVolumeDriver,
                     self).get_config(connection_info, disk_info)
        data = connection_info['data']
        conf.source_protocol = SOURCE_PROTOCOL
        conf.source_type = SOURCE_TYPE
        conf.driver_cache = DRIVER_CACHE
        conf.driver_io = DRIVER_IO
        conf.driver_format = data.get('format', 'raw')

        conf.source_path = self._get_device_path(connection_info)

        return conf

    @utils.synchronized('connect_qb_volume')
    def connect_volume(self, connection_info, instance):
        """Connect the volume."""
        if is_systemd():
            LOG.debug("systemd detected.")
        else:
            LOG.debug("No systemd detected.")

        data = connection_info['data']
        quobyte_volume = self._normalize_export(data['export'])
        mount_path = self._get_mount_path(connection_info)
        mounted = libvirt_utils.is_mounted(mount_path,
                                           SOURCE_PROTOCOL
                                           + '@' + quobyte_volume)
        if mounted:
            try:
                os.stat(mount_path)
            except OSError as exc:
                if exc.errno == errno.ENOTCONN:
                    mounted = False
                    LOG.info('Fixing previous mount %s which was not'
                             ' unmounted correctly.', mount_path)
                    umount_volume(mount_path)

        if not mounted:
            mount_volume(quobyte_volume,
                         mount_path,
                         CONF.libvirt.quobyte_client_cfg)

        validate_volume(mount_path)

    @utils.synchronized('connect_qb_volume')
    def disconnect_volume(self, connection_info, instance):
        """Disconnect the volume."""

        quobyte_volume = self._normalize_export(
                                        connection_info['data']['export'])
        mount_path = self._get_mount_path(connection_info)

        if libvirt_utils.is_mounted(mount_path, 'quobyte@' + quobyte_volume):
            umount_volume(mount_path)
        else:
            LOG.info("Trying to disconnected unmounted volume at %s",
                     mount_path)

    def _normalize_export(self, export):
        protocol = SOURCE_PROTOCOL + "://"
        if export.startswith(protocol):
            export = export[len(protocol):]
        return export
