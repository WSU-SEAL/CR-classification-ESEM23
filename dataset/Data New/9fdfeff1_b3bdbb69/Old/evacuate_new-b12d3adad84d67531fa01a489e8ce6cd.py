# Copyright 2014 NEC Corporation.  All rights reserved.
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

import copy

from nova.api.validation import parameter_types


evacuate = {
    'type': 'object',
    'properties': {
        'evacuate': {
            'type': 'object',
            'properties': {
                'host': parameter_types.hostname,
                'onSharedStorage': parameter_types.boolean,
                'adminPass': parameter_types.admin_password,
            },
            'required': ['onSharedStorage'],
            'additionalProperties': False,
        },
    },
    'required': ['evacuate'],
    'additionalProperties': False,
}

evacuate_v214 = copy.deepcopy(evacuate)
del evacuate_v214['properties']['evacuate']['properties']['onSharedStorage']
del evacuate_v214['properties']['evacuate']['required']

evacuate_v2_29 = copy.deepcopy(evacuate_v214)
evacuate_v2_29['properties']['evacuate']['properties'][
    'force'] = parameter_types.boolean

# v2.68 removes the 'force' parameter added in v2.29, meaning it is essentially
# identical to v2.14
evacuate_v2_68 = copy.deepcopy(evacuate_v214)
