# Copyright (c) 2014 Red Hat, Inc.
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

from nova.scheduler.client import query
from nova.scheduler.client import report
from nova.scheduler import utils


class SchedulerClient(object):
    """Client library for placing calls to the scheduler."""

    def __init__(self):
        self.queryclient = query.SchedulerQueryClient()
        self.reportclient = report.SchedulerReportClient()

    @utils.retry_select_destinations
    def select_destinations(self, context, spec_obj, instance_uuids,
            return_objects=False, return_alternates=False):
        return self.queryclient.select_destinations(context, spec_obj,
                instance_uuids, return_objects, return_alternates)

    def update_aggregates(self, context, aggregates):
        self.queryclient.update_aggregates(context, aggregates)

    def delete_aggregate(self, context, aggregate):
        self.queryclient.delete_aggregate(context, aggregate)

    def set_inventory_for_provider(self, context, rp_uuid, rp_name, inv_data,
                                   parent_provider_uuid=None):
        self.reportclient.set_inventory_for_provider(
            context,
            rp_uuid,
            rp_name,
            inv_data,
            parent_provider_uuid=parent_provider_uuid,
        )

    def update_compute_node(self, context, compute_node):
        self.reportclient.update_compute_node(context, compute_node)

    def update_instance_info(self, context, host_name, instance_info):
        self.queryclient.update_instance_info(context, host_name,
                                              instance_info)

    def delete_instance_info(self, context, host_name, instance_uuid):
        self.queryclient.delete_instance_info(context, host_name,
                                              instance_uuid)

    def sync_instance_info(self, context, host_name, instance_uuids):
        self.queryclient.sync_instance_info(context, host_name, instance_uuids)
