# Copyright 2016 OpenStack Foundation
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

"""The 'workarounds' group is for very specific reasons.

If you're:

 - Working around an issue in a system tool (e.g. libvirt or qemu) where the
   fix is in flight/discussed in that community.
 - The tool can be/is fixed in some distributions and rather than patch the
   code those distributions can trivially set a config option to get the
   "correct" behavior.

Then this is a good place for your workaround.

.. warning::

  Please use with care! Document the BugID that your workaround is paired with.
"""

from oslo_config import cfg

workarounds_group = cfg.OptGroup(
    'workarounds',
    title='Workaround Options',
    help="""
A collection of workarounds used to mitigate bugs or issues found in system
tools (e.g. Libvirt or QEMU) or Nova itself under certain conditions. These
should only be enabled in exceptional circumstances. All options are linked
against bug IDs, where more information on the issue can be found.
""")
ALL_OPTS = [
    cfg.BoolOpt(
        'disable_rootwrap',
        default=False,
        help="""
Use sudo instead of rootwrap.

Allow fallback to sudo for performance reasons.

For more information, refer to the bug report:

  https://bugs.launchpad.net/nova/+bug/1415106

Possible values:

* True: Use sudo instead of rootwrap
* False: Use rootwrap as usual

Interdependencies to other options:

* Any options that affect 'rootwrap' will be ignored.
"""),

    cfg.BoolOpt(
        'disable_libvirt_livesnapshot',
        default=False,
        help="""
Disable live snapshots when using the libvirt driver.

Live snapshots allow the snapshot of the disk to happen without an
interruption to the guest, using coordination with a guest agent to
quiesce the filesystem.

When using libvirt 1.2.2 live snapshots fail intermittently under load
(likely related to concurrent libvirt/qemu operations). This config
option provides a mechanism to disable live snapshot, in favor of cold
snapshot, while this is resolved. Cold snapshot causes an instance
outage while the guest is going through the snapshotting process.

For more information, refer to the bug report:

  https://bugs.launchpad.net/nova/+bug/1334398

Possible values:

* True: Live snapshot is disabled when using libvirt
* False: Live snapshots are always used when snapshotting (as long as
  there is a new enough libvirt and the backend storage supports it)
"""),

    cfg.BoolOpt(
        'handle_virt_lifecycle_events',
        default=True,
        help="""
Enable handling of events emitted from compute drivers.

Many compute drivers emit lifecycle events, which are events that occur when,
for example, an instance is starting or stopping. If the instance is going
through task state changes due to an API operation, like resize, the events
are ignored.

This is an advanced feature which allows the hypervisor to signal to the
compute service that an unexpected state change has occurred in an instance
and that the instance can be shutdown automatically. Unfortunately, this can
race in some conditions, for example in reboot operations or when the compute
service or when host is rebooted (planned or due to an outage). If such races
are common, then it is advisable to disable this feature.

Care should be taken when this feature is disabled and
'sync_power_state_interval' is set to a negative value. In this case, any
instances that get out of sync between the hypervisor and the Nova database
will have to be synchronized manually.

For more information, refer to the bug report:

  https://bugs.launchpad.net/bugs/1444630

Interdependencies to other options:

* If ``sync_power_state_interval`` is negative and this feature is disabled,
  then instances that get out of sync between the hypervisor and the Nova
  database will have to be synchronized manually.
"""),

    cfg.BoolOpt(
        'disable_group_policy_check_upcall',
        default=False,
        help="""
Disable the server group policy check upcall in compute.

In order to detect races with server group affinity policy, the compute
service attempts to validate that the policy was not violated by the
scheduler. It does this by making an upcall to the API database to list
the instances in the server group for one that it is booting, which violates
our api/cell isolation goals. Eventually this will be solved by proper affinity
guarantees in the scheduler and placement service, but until then, this late
check is needed to ensure proper affinity policy.

Operators that desire api/cell isolation over this check should
enable this flag, which will avoid making that upcall from compute.

Related options:

* [filter_scheduler]/track_instance_changes also relies on upcalls from the
  compute service to the scheduler service.
"""),

    cfg.BoolOpt(
        'enable_consoleauth',
        default=False,
        deprecated_for_removal=True,
        deprecated_since="18.0.0",
        deprecated_reason="""
This option has been added as deprecated originally because it is used
for avoiding a upgrade issue and it will not be used in the future.
See the help text for more details.
""",
        help="""
Enable the consoleauth service to avoid resetting unexpired consoles.

Console token authorizations have moved from the ``nova-consoleauth`` service
to the database, so all new consoles will be supported by the database backend.
With this, consoles that existed before database backend support will be reset.
For most operators, this should be a minimal disruption as the default TTL of a
console token is 10 minutes.

Operators that have much longer token TTL configured or otherwise wish to avoid
immediately resetting all existing consoles can enable this flag to continue
using the ``nova-consoleauth`` service in addition to the database backend.
Once all of the old ``nova-consoleauth`` supported console tokens have expired,
this flag should be disabled. For example, if a deployment has configured a
token TTL of one hour, the operator may disable the flag, one hour after
deploying the new code during an upgrade.

.. note:: Cells v1 was not converted to use the database backend for
  console token authorizations. Cells v1 console token authorizations will
  continue to be supported by the ``nova-consoleauth`` service and use of
  the ``[workarounds]/enable_consoleauth`` option does not apply to
  Cells v1 users.

Related options:

* ``[consoleauth]/token_ttl``
"""),
    cfg.BoolOpt(
        'ensure_libvirt_evac_instance_dir_cleanup_rbd',
        default=False,
        help="""
Ensure that the instance directory is cleaned during an evacuation with RBD.

When enabled this workaround will ensure that the instance directory is cleaned
regardless of the backing instance disks not being removed from RBD during an
evacuation. This will allow the instance to return to the local host in future
without encountering issues due to the instance directory already existing.

.. note:: Operators will need to ensure that the instance directory itself is
not shared between computes before enabling this workaround otherwise the
``console.log`` for the instance will be lost.
"""),
]


def register_opts(conf):
    conf.register_group(workarounds_group)
    conf.register_opts(ALL_OPTS, group=workarounds_group)


def list_opts():
    return {workarounds_group: ALL_OPTS}
