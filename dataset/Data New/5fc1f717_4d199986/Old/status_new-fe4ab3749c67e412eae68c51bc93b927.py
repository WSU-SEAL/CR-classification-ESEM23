# Copyright 2016 IBM Corp.
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

"""
CLI interface for nova status commands.
"""

from __future__ import print_function

import collections
import functools
import sys
import traceback

from keystoneauth1 import exceptions as ks_exc
from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_upgradecheck import upgradecheck
import pkg_resources
from sqlalchemy import func as sqlfunc
from sqlalchemy import MetaData, Table, and_, select
from sqlalchemy.sql import false

from nova.cmd import common as cmd_common
import nova.conf
from nova import config
from nova import context as nova_context
from nova.db.sqlalchemy import api as db_session
from nova.i18n import _
from nova.objects import cell_mapping as cell_mapping_obj
from nova import utils
from nova import version

CONF = nova.conf.CONF

PLACEMENT_DOCS_LINK = 'https://docs.openstack.org/nova/latest' \
                      '/user/placement.html'

# NOTE(efried): 1.30 is required by nova-compute to support resource provider
# reshaping (inventory and allocation data migration).
# NOTE: If you bump this version, remember to update the history
# section in the nova-status man page (doc/source/cli/nova-status).
MIN_PLACEMENT_MICROVERSION = "1.30"


class UpgradeCommands(upgradecheck.UpgradeCommands):
    """Commands related to upgrades.

    The subcommands here must not rely on the nova object model since they
    should be able to run on n-1 data. Any queries to the database should be
    done through the sqlalchemy query language directly like the database
    schema migrations.
    """

    def _count_compute_nodes(self, context=None):
        """Returns the number of compute nodes in the cell database."""
        # NOTE(mriedem): This does not filter based on the service status
        # because a disabled nova-compute service could still be reporting
        # inventory info to the placement service. There could be an outside
        # chance that there are compute node records in the database for
        # disabled nova-compute services that aren't yet upgraded to Ocata or
        # the nova-compute service was deleted and the service isn't actually
        # running on the compute host but the operator hasn't cleaned up the
        # compute_nodes entry in the database yet. We consider those edge cases
        # here and the worst case scenario is we give a warning that there are
        # more compute nodes than resource providers. We can tighten this up
        # later if needed, for example by not including compute nodes that
        # don't have a corresponding nova-compute service in the services
        # table, or by only counting compute nodes with a service version of at
        # least 15 which was the highest service version when Newton was
        # released.
        meta = MetaData(bind=db_session.get_engine(context=context))
        compute_nodes = Table('compute_nodes', meta, autoload=True)
        return select([sqlfunc.count()]).select_from(compute_nodes).where(
                compute_nodes.c.deleted == 0).scalar()

    def _check_cellsv2(self):
        """Checks to see if cells v2 has been setup.

        These are the same checks performed in the 030_require_cell_setup API
        DB migration except we expect this to be run AFTER the
        nova-manage cell_v2 simple_cell_setup command, which would create the
        cell and host mappings and sync the cell0 database schema, so we don't
        check for flavors at all because you could create those after doing
        this on an initial install. This also has to be careful about checking
        for compute nodes if there are no host mappings on a fresh install.
        """
        meta = MetaData()
        meta.bind = db_session.get_api_engine()

        cell_mappings = self._get_cell_mappings()
        count = len(cell_mappings)
        # Two mappings are required at a minimum, cell0 and your first cell
        if count < 2:
            msg = _('There needs to be at least two cell mappings, one for '
                    'cell0 and one for your first cell. Run command '
                    '\'nova-manage cell_v2 simple_cell_setup\' and then '
                    'retry.')
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)

        cell0 = any(mapping.is_cell0() for mapping in cell_mappings)
        if not cell0:
            msg = _('No cell0 mapping found. Run command '
                    '\'nova-manage cell_v2 simple_cell_setup\' and then '
                    'retry.')
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)

        host_mappings = Table('host_mappings', meta, autoload=True)
        count = select([sqlfunc.count()]).select_from(host_mappings).scalar()
        if count == 0:
            # This may be a fresh install in which case there may not be any
            # compute_nodes in the cell database if the nova-compute service
            # hasn't started yet to create those records. So let's query the
            # cell database for compute_nodes records and if we find at least
            # one it's a failure.
            num_computes = self._count_compute_nodes()
            if num_computes > 0:
                msg = _('No host mappings found but there are compute nodes. '
                        'Run command \'nova-manage cell_v2 '
                        'simple_cell_setup\' and then retry.')
                return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)

            msg = _('No host mappings or compute nodes were found. Remember '
                    'to run command \'nova-manage cell_v2 discover_hosts\' '
                    'when new compute hosts are deployed.')
            return upgradecheck.Result(upgradecheck.Code.SUCCESS, msg)

        return upgradecheck.Result(upgradecheck.Code.SUCCESS)

    @staticmethod
    def _placement_get(path):
        """Do an HTTP get call against placement engine.

        This is in a dedicated method to make it easier for unit
        testing purposes.

        """
        client = utils.get_ksa_adapter('placement')
        return client.get(path, raise_exc=True).json()

    def _check_placement(self):
        """Checks to see if the placement API is ready for scheduling.

        Checks to see that the placement API service is registered in the
        service catalog and that we can make requests against it.
        """
        try:
            # TODO(efried): Use ksa's version filtering in _placement_get
            versions = self._placement_get("/")
            max_version = pkg_resources.parse_version(
                versions["versions"][0]["max_version"])
            needs_version = pkg_resources.parse_version(
                MIN_PLACEMENT_MICROVERSION)
            if max_version < needs_version:
                msg = (_('Placement API version %(needed)s needed, '
                         'you have %(current)s.') %
                       {'needed': needs_version, 'current': max_version})
                return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)
        except ks_exc.MissingAuthPlugin:
            msg = _('No credentials specified for placement API in nova.conf.')
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)
        except ks_exc.Unauthorized:
            msg = _('Placement service credentials do not work.')
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)
        except ks_exc.EndpointNotFound:
            msg = _('Placement API endpoint not found.')
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)
        except ks_exc.DiscoveryFailure:
            msg = _('Discovery for placement API URI failed.')
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)
        except ks_exc.NotFound:
            msg = _('Placement API does not seem to be running.')
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)

        return upgradecheck.Result(upgradecheck.Code.SUCCESS)

    @staticmethod
    def _get_non_cell0_mappings():
        """Queries the API database for non-cell0 cell mappings.

        :returns: list of nova.objects.CellMapping objects
        """
        return UpgradeCommands._get_cell_mappings(include_cell0=False)

    @staticmethod
    def _get_cell_mappings(include_cell0=True):
        """Queries the API database for cell mappings.

        .. note:: This method is unique in that it queries the database using
                  CellMappingList.get_all() rather than a direct query using
                  the sqlalchemy models. This is because
                  CellMapping.database_connection can be a template and the
                  object takes care of formatting the URL. We cannot use
                  RowProxy objects from sqlalchemy because we cannot set the
                  formatted 'database_connection' value back on those objects
                  (they are read-only).

        :param include_cell0: True if cell0 should be returned, False if cell0
            should be excluded from the results.
        :returns: list of nova.objects.CellMapping objects
        """
        ctxt = nova_context.get_admin_context()
        cell_mappings = cell_mapping_obj.CellMappingList.get_all(ctxt)
        if not include_cell0:
            # Since CellMappingList does not implement remove() we have to
            # create a new list and exclude cell0.
            mappings = [mapping for mapping in cell_mappings
                        if not mapping.is_cell0()]
            cell_mappings = cell_mapping_obj.CellMappingList(objects=mappings)
        return cell_mappings

    @staticmethod
    def _is_ironic_instance_migrated(extras, inst):
        extra = (extras.select().where(extras.c.instance_uuid == inst['uuid']
                                       ).execute().first())
        # Pull the flavor and deserialize it. Note that the flavor info for an
        # instance is a dict keyed by "cur", "old", "new" and we want the
        # current flavor.
        flavor = jsonutils.loads(extra['flavor'])['cur']['nova_object.data']
        # Do we have a custom resource flavor extra spec?
        specs = flavor['extra_specs'] if 'extra_specs' in flavor else {}
        for spec_key in specs:
            if spec_key.startswith('resources:CUSTOM_'):
                # We found a match so this instance is good.
                return True
        return False

    def _check_ironic_flavor_migration(self):
        """In Pike, ironic instances and flavors need to be migrated to use
        custom resource classes. In ironic, the node.resource_class should be
        set to some custom resource class value which should match a
        "resources:<custom resource class name>" flavor extra spec on baremetal
        flavors. Existing ironic instances will have their embedded
        instance.flavor.extra_specs migrated to use the matching ironic
        node.resource_class value in the nova-compute service, or they can
        be forcefully migrated using "nova-manage db ironic_flavor_migration".

        In this check, we look for all ironic compute nodes in all non-cell0
        cells, and from those ironic compute nodes, we look for an instance
        that has a "resources:CUSTOM_*" key in it's embedded flavor extra
        specs.
        """
        cell_mappings = self._get_non_cell0_mappings()
        ctxt = nova_context.get_admin_context()
        # dict of cell identifier (name or uuid) to number of unmigrated
        # instances
        unmigrated_instance_count_by_cell = collections.defaultdict(int)
        for cell_mapping in cell_mappings:
            with nova_context.target_cell(ctxt, cell_mapping) as cctxt:
                # Get the (non-deleted) ironic compute nodes in this cell.
                meta = MetaData(bind=db_session.get_engine(context=cctxt))
                compute_nodes = Table('compute_nodes', meta, autoload=True)
                ironic_nodes = (
                    compute_nodes.select().where(and_(
                        compute_nodes.c.hypervisor_type == 'ironic',
                        compute_nodes.c.deleted == 0
                    )).execute().fetchall())

                if ironic_nodes:
                    # We have ironic nodes in this cell, let's iterate over
                    # them looking for instances.
                    instances = Table('instances', meta, autoload=True)
                    extras = Table('instance_extra', meta, autoload=True)
                    for node in ironic_nodes:
                        nodename = node['hypervisor_hostname']
                        # Get any (non-deleted) instances for this node.
                        ironic_instances = (
                            instances.select().where(and_(
                                instances.c.node == nodename,
                                instances.c.deleted == 0
                            )).execute().fetchall())
                        # Get the instance_extras for each instance so we can
                        # find the flavors.
                        for inst in ironic_instances:
                            if not self._is_ironic_instance_migrated(
                                    extras, inst):
                                # We didn't find the extra spec key for this
                                # instance so increment the number of
                                # unmigrated instances in this cell.
                                unmigrated_instance_count_by_cell[
                                    cell_mapping.uuid] += 1

        if not cell_mappings:
            # There are no non-cell0 mappings so we can't determine this, just
            # return a warning. The cellsv2 check would have already failed
            # on this.
            msg = (_('Unable to determine ironic flavor migration without '
                     'cell mappings.'))
            return upgradecheck.Result(upgradecheck.Code.WARNING, msg)

        if unmigrated_instance_count_by_cell:
            # There are unmigrated ironic instances, so we need to fail.
            msg = (_('There are (cell=x) number of unmigrated instances in '
                     'each cell: %s. Run \'nova-manage db '
                     'ironic_flavor_migration\' on each cell.') %
                   ' '.join('(%s=%s)' % (
                       cell_id, unmigrated_instance_count_by_cell[cell_id])
                            for cell_id in
                            sorted(unmigrated_instance_count_by_cell.keys())))
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)

        # Either there were no ironic compute nodes or all instances for
        # those nodes are already migrated, so there is nothing to do.
        return upgradecheck.Result(upgradecheck.Code.SUCCESS)

    def _get_min_service_version(self, context, binary):
        meta = MetaData(bind=db_session.get_engine(context=context))
        services = Table('services', meta, autoload=True)
        return select([sqlfunc.min(services.c.version)]).select_from(
            services).where(and_(
                services.c.binary == binary,
                services.c.deleted == 0,
                services.c.forced_down == false())).scalar()

    def _check_request_spec_migration(self):
        """Checks to make sure request spec migrations are complete.

        Iterates all cells checking to see that non-deleted instances have
        a matching request spec in the API database. This is necessary in order
        to drop the migrate_instances_add_request_spec online data migration
        and accompanying compatibility code found through nova-api and
        nova-conductor.
        """
        meta = MetaData(bind=db_session.get_api_engine())
        mappings = self._get_cell_mappings()

        if not mappings:
            # There are no cell mappings so we can't determine this, just
            # return a warning. The cellsv2 check would have already failed
            # on this.
            msg = (_('Unable to determine request spec migrations without '
                     'cell mappings.'))
            return upgradecheck.Result(upgradecheck.Code.WARNING, msg)

        request_specs = Table('request_specs', meta, autoload=True)
        ctxt = nova_context.get_admin_context()
        incomplete_cells = []  # list of cell mapping uuids
        for mapping in mappings:
            with nova_context.target_cell(ctxt, mapping) as cctxt:
                # Get all instance uuids for non-deleted instances in this
                # cell.
                meta = MetaData(bind=db_session.get_engine(context=cctxt))
                instances = Table('instances', meta, autoload=True)
                instance_records = (
                    select([instances.c.uuid]).select_from(instances).where(
                        instances.c.deleted == 0
                    ).execute().fetchall())
                # For each instance in the list, verify that it has a matching
                # request spec in the API DB.
                for inst in instance_records:
                    spec_id = (
                        select([request_specs.c.id]).select_from(
                            request_specs).where(
                            request_specs.c.instance_uuid == inst['uuid']
                        ).execute().scalar())
                    if spec_id is None:
                        # This cell does not have all of its instances
                        # migrated for request specs so track it and move on.
                        incomplete_cells.append(mapping.uuid)
                        break

        # It's a failure if there are any unmigrated instances at this point
        # because we are planning to drop the online data migration routine and
        # compatibility code in Stein.
        if incomplete_cells:
            msg = (_("The following cells have instances which do not have "
                     "matching request_specs in the API database: %s Run "
                     "'nova-manage db online_data_migrations' on each cell "
                     "to create the missing request specs.") %
                   ', '.join(incomplete_cells))
            return upgradecheck.Result(upgradecheck.Code.FAILURE, msg)
        return upgradecheck.Result(upgradecheck.Code.SUCCESS)

    def _check_console_auths(self):
        """Checks for console usage and warns with info for rolling upgrade.

        Iterates all cells checking to see if the nova-consoleauth service is
        non-deleted/non-disabled and whether there are any console token auths
        in that cell database. If there is a nova-consoleauth service being
        used and no console token auths in the cell database, emit a warning
        telling the user to set [workarounds]enable_consoleauth = True if they
        are performing a rolling upgrade.
        """
        # If we're using cells v1, we don't need to check if the workaround
        # needs to be used because cells v1 always uses nova-consoleauth.
        # If the operator has already enabled the workaround, we don't need
        # to check anything.
        if CONF.cells.enable or CONF.workarounds.enable_consoleauth:
            return upgradecheck.Result(upgradecheck.Code.SUCCESS)

        # We need to check cell0 for nova-consoleauth service records because
        # it's possible a deployment could have services stored in the cell0
        # database, if they've defaulted their [database]connection in
        # nova.conf to cell0.
        mappings = self._get_cell_mappings()

        if not mappings:
            # There are no cell mappings so we can't determine this, just
            # return a warning. The cellsv2 check would have already failed
            # on this.
            msg = (_('Unable to check consoles without cell mappings.'))
            return upgradecheck.Result(upgradecheck.Code.WARNING, msg)

        ctxt = nova_context.get_admin_context()
        # If we find a non-deleted, non-disabled nova-consoleauth service in
        # any cell, we will assume the deployment is using consoles.
        using_consoles = False
        for mapping in mappings:
            with nova_context.target_cell(ctxt, mapping) as cctxt:
                # Check for any non-deleted, non-disabled nova-consoleauth
                # service.
                meta = MetaData(bind=db_session.get_engine(context=cctxt))
                services = Table('services', meta, autoload=True)
                consoleauth_service_record = (
                    select([services.c.id]).select_from(services).where(and_(
                        services.c.binary == 'nova-consoleauth',
                        services.c.deleted == 0,
                        services.c.disabled == false())).execute().first())
                if consoleauth_service_record:
                    using_consoles = True
                    break

        if using_consoles:
            # If the deployment is using consoles, we can only be certain the
            # upgrade is complete if each compute service is >= Rocky and
            # supports storing console token auths in the database backend.
            for mapping in mappings:
                # Skip cell0 as no compute services should be in it.
                if mapping.is_cell0():
                    continue
                # Get the minimum nova-compute service version in this
                # cell.
                with nova_context.target_cell(ctxt, mapping) as cctxt:
                    min_version = self._get_min_service_version(
                        cctxt, 'nova-compute')
                    # We could get None for the minimum version in the case of
                    # new install where there are no computes. If there are
                    # compute services, they should all have versions.
                    if min_version is not None and min_version < 35:
                        msg = _("One or more cells were found which have "
                                "nova-compute services older than Rocky. "
                                "Please set the "
                                "'[workarounds]enable_consoleauth' "
                                "configuration option to 'True' on your "
                                "console proxy host if you are performing a "
                                "rolling upgrade to enable consoles to "
                                "function during a partial upgrade.")
                        return upgradecheck.Result(upgradecheck.Code.WARNING,
                                                  msg)

        return upgradecheck.Result(upgradecheck.Code.SUCCESS)

    # The format of the check functions is to return an upgradecheck.Result
    # object with the appropriate upgradecheck.Code and details set. If the
    # check hits warnings or failures then those should be stored in the
    # returned upgradecheck.Result's "details" attribute. The summary will
    # be rolled up at the end of the check() function. These functions are
    # intended to be run in order and build on top of each other so order
    # matters.
    _upgrade_checks = (
        # Added in Ocata
        (_('Cells v2'), _check_cellsv2),
        # Added in Ocata
        (_('Placement API'), _check_placement),
        # Added in Rocky (but also useful going back to Pike)
        (_('Ironic Flavor Migration'), _check_ironic_flavor_migration),
        # Added in Rocky
        (_('Request Spec Migration'), _check_request_spec_migration),
        # Added in Stein (but also useful going back to Rocky)
        (_('Console Auths'), _check_console_auths),
    )


CATEGORIES = {
    'upgrade': UpgradeCommands,
}


add_command_parsers = functools.partial(cmd_common.add_command_parsers,
                                        categories=CATEGORIES)


category_opt = cfg.SubCommandOpt('category',
                                 title='Command categories',
                                 help='Available categories',
                                 handler=add_command_parsers)


def main():
    """Parse options and call the appropriate class/method."""
    CONF.register_cli_opt(category_opt)
    config.parse_args(sys.argv)

    if CONF.category.name == "version":
        print(version.version_string_with_package())
        return 0

    if CONF.category.name == "bash-completion":
        cmd_common.print_bash_completion(CATEGORIES)
        return 0

    try:
        fn, fn_args, fn_kwargs = cmd_common.get_action_fn()
        ret = fn(*fn_args, **fn_kwargs)
        return ret
    except Exception:
        print(_('Error:\n%s') % traceback.format_exc())
        # This is 255 so it's not confused with the upgrade check exit codes.
        return 255
