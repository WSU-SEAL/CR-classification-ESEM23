# Copyright 2010 OpenStack Foundation
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

import six
import webob

from nova.api.openstack import common
from nova.api.openstack.compute.schemas import flavors_extraspecs
from nova.api.openstack import wsgi
from nova.api import validation
from nova import exception
from nova.i18n import _
from nova.objects import fields
from nova.objects import image_meta
from nova.policies import flavor_extra_specs as fes_policies
from nova import utils
from nova.virt import hardware

# flavor extra specs keys needed for multiple validation routines
CPU_POLICY_KEY = 'hw:cpu_policy'


class FlavorExtraSpecsController(wsgi.Controller):
    """The flavor extra specs API controller for the OpenStack API."""

    def _check_flavor_in_use(self, flavor):
        if flavor.is_in_use():
            msg = _('Updating extra specs not permitted when flavor is '
                    'associated to one or more valid instances')
            raise webob.exc.HTTPBadRequest(explanation=msg)

    @staticmethod
    def _validate_numa_node(flavor):
        NUMA_NODES_KEY = 'hw:numa_nodes'
        specs = flavor.extra_specs
        try:
            hw_numa_nodes = int(specs.get(NUMA_NODES_KEY, 1))
        except ValueError:
            msg = _('hw:numa_nodes value must be an integer')
            raise webob.exc.HTTPBadRequest(explanation=msg)
        if hw_numa_nodes < 1:
            msg = _('hw:numa_nodes value must be greater than 0')
            raise webob.exc.HTTPBadRequest(explanation=msg)

        # Do common error check from numa_get_constraints with a clearer error
        if hw_numa_nodes > 1 and specs.get('hw:numa_cpus.0') is None:
            if (flavor.vcpus % hw_numa_nodes) > 0:
                msg = _('flavor vcpus not evenly divisible by'
                        ' the specified hw:numa_nodes value (%s)') \
                      % hw_numa_nodes
                raise webob.exc.HTTPConflict(explanation=msg)

            if (flavor.memory_mb % hw_numa_nodes) > 0:
                msg = _('flavor memory not evenly divisible by'
                        ' the specified hw:numa_nodes value (%s) so'
                        ' per NUMA-node values must be explicitly specified') \
                      % hw_numa_nodes
                raise webob.exc.HTTPConflict(explanation=msg)

        # Catchall test
        try:
            # Check if this modified flavor would be valid assuming
            # no image metadata.
            hardware.numa_get_constraints(flavor, image_meta.ImageMeta(
                    properties=image_meta.ImageMetaProps()))
        except Exception as error:
            msg = _('%s') % error.message
            raise webob.exc.HTTPConflict(explanation=msg)

    @staticmethod
    def _validate_cpu_policy(flavor):
        key = CPU_POLICY_KEY
        specs = flavor.extra_specs
        if key in specs:
            value = specs[key]
            if value not in fields.CPUAllocationPolicy.ALL:
                msg = _("invalid %(K)s '%(V)s', must be one of: %(A)s") \
                        % {'K': key,
                           'V': value,
                           'A': ', '.join(
                            list(fields.CPUAllocationPolicy.ALL))}
                raise webob.exc.HTTPBadRequest(explanation=msg)

    @staticmethod
    def _validate_cpu_thread_policy(flavor):
        key = 'hw:cpu_thread_policy'
        specs = flavor.extra_specs
        if key in specs:
            value = specs[key]
            if value not in fields.CPUThreadAllocationPolicy.ALL:
                msg = _("invalid %(K)s '%(V)s', must be one of %(A)s") \
                        % {'K': key,
                           'V': value,
                           'A': ', '.join(
                            list(fields.CPUThreadAllocationPolicy.ALL))}
                raise webob.exc.HTTPBadRequest(explanation=msg)
            if specs.get(CPU_POLICY_KEY) != \
                    fields.CPUAllocationPolicy.DEDICATED:
                msg = _('%(K)s is only valid when %(P)s is %(D)s.  Either '
                        'unset %(K)s or set %(P)s to %(D)s.') \
                        % {'K': key,
                           'P': CPU_POLICY_KEY,
                           'D': fields.CPUAllocationPolicy.DEDICATED}
                raise webob.exc.HTTPConflict(explanation=msg)

    def _validate_extra_specs(self, flavor):
        self._validate_cpu_policy(flavor)
        self._validate_cpu_thread_policy(flavor)
        self._validate_numa_node(flavor)

    def _get_extra_specs(self, context, flavor_id):
        flavor = common.get_flavor(context, flavor_id)
        return dict(extra_specs=flavor.extra_specs)

    # NOTE(gmann): Max length for numeric value is being checked
    # explicitly as json schema cannot have max length check for numeric value
    def _check_extra_specs_value(self, specs):
        for value in specs.values():
            try:
                if isinstance(value, (six.integer_types, float)):
                    value = six.text_type(value)
                    utils.check_string_length(value, 'extra_specs value',
                                              max_length=255)
            except exception.InvalidInput as error:
                raise webob.exc.HTTPBadRequest(
                          explanation=error.format_message())

    @wsgi.expected_errors(404)
    def index(self, req, flavor_id):
        """Returns the list of extra specs for a given flavor."""
        context = req.environ['nova.context']
        context.can(fes_policies.POLICY_ROOT % 'index')
        return self._get_extra_specs(context, flavor_id)

    # NOTE(gmann): Here should be 201 instead of 200 by v2.1
    # +microversions because the flavor extra specs has been created
    # completely when returning a response.
    @wsgi.expected_errors((400, 404, 409))
    @validation.schema(flavors_extraspecs.create)
    def create(self, req, flavor_id, body):
        context = req.environ['nova.context']
        context.can(fes_policies.POLICY_ROOT % 'create')

        specs = body['extra_specs']
        self._check_extra_specs_value(specs)
        flavor = common.get_flavor(context, flavor_id)
        self._check_flavor_in_use(flavor)
        try:
            flavor.extra_specs = dict(flavor.extra_specs, **specs)
            self._validate_extra_specs(flavor)
            flavor.save()
        except exception.FlavorExtraSpecUpdateCreateFailed as e:
            raise webob.exc.HTTPConflict(explanation=e.format_message())
        except exception.FlavorNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())
        return body

    @wsgi.expected_errors((400, 404, 409))
    @validation.schema(flavors_extraspecs.update)
    def update(self, req, flavor_id, id, body):
        context = req.environ['nova.context']
        context.can(fes_policies.POLICY_ROOT % 'update')

        self._check_extra_specs_value(body)
        if id not in body:
            expl = _('Request body and URI mismatch')
            raise webob.exc.HTTPBadRequest(explanation=expl)
        flavor = common.get_flavor(context, flavor_id)
        self._check_flavor_in_use(flavor)
        try:
            flavor.extra_specs = dict(flavor.extra_specs, **body)
            self._validate_extra_specs(flavor)
            flavor.save()
        except exception.FlavorExtraSpecUpdateCreateFailed as e:
            raise webob.exc.HTTPConflict(explanation=e.format_message())
        except exception.FlavorNotFound as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())
        return body

    @wsgi.expected_errors(404)
    def show(self, req, flavor_id, id):
        """Return a single extra spec item."""
        context = req.environ['nova.context']
        context.can(fes_policies.POLICY_ROOT % 'show')
        flavor = common.get_flavor(context, flavor_id)
        try:
            return {id: flavor.extra_specs[id]}
        except KeyError:
            msg = _("Flavor %(flavor_id)s has no extra specs with "
                    "key %(key)s.") % dict(flavor_id=flavor_id,
                                           key=id)
            raise webob.exc.HTTPNotFound(explanation=msg)

    # NOTE(gmann): Here should be 204(No Content) instead of 200 by v2.1
    # +microversions because the flavor extra specs has been deleted
    # completely when returning a response.
    @wsgi.expected_errors((400, 404, 409))
    def delete(self, req, flavor_id, id):
        """Deletes an existing extra spec."""
        context = req.environ['nova.context']
        context.can(fes_policies.POLICY_ROOT % 'delete')
        flavor = common.get_flavor(context, flavor_id)
        self._check_flavor_in_use(flavor)
        try:
            # The id object is an aggregation of multiple extra spec keys
            # The keys are aggregated using the ';'  character
            # This allows multiple extra specs to be deleted in one call
            # This is required since some validators will raise an exception
            # if one extra spec exists while another is missing
            ids = id.split(';')
            for an_id in ids:
                del flavor.extra_specs[an_id]
            self._validate_extra_specs(flavor)
            flavor.save()
        except (exception.FlavorExtraSpecsNotFound,
                exception.FlavorNotFound) as e:
            raise webob.exc.HTTPNotFound(explanation=e.format_message())
        except KeyError:
            msg = _("Flavor %(flavor_id)s has no extra specs with "
                    "key %(key)s.") % dict(flavor_id=flavor_id,
                                           key=id)
            raise webob.exc.HTTPNotFound(explanation=msg)
