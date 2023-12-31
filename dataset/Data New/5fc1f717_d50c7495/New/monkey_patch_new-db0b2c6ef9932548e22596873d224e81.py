# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# Copyright 2019 Red Hat, Inc.
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

"""Enable eventlet monkey patching."""

# NOTE(mdbooth): Anything imported here will not be monkey patched. It is
# important to take care not to import anything here which requires monkey
# patching.

import eventlet
import os
import sys

# NOTE(mdbooth): Imports only sys (2019-01-30). Other modules imported at
# runtime on execution of debugger.init().
from nova import debugger

# Assert that modules with known monkey-patching issues have not been imported
# before monkey patching
# urllib3: https://bugs.launchpad.net/nova/+bug/1808951
# oslo_context.context: https://bugs.launchpad.net/nova/+bug/1773102
for module in ('urllib3', 'oslo_context.context'):
    assert module not in sys.modules, \
           "%s loaded before monkey patching" % module

# See https://bugs.launchpad.net/nova/+bug/1164822
# TODO(mdbooth): This feature was deprecated and removed in eventlet at some
# point but brought back in version 0.21.0, presumably because some users still
# required it to work round issues. However, there have been a number of
# greendns fixes in eventlet since then. Specifically, it looks as though the
# originally reported IPv6 issue may have been fixed in version 0.24.0. We
# should remove this when we can confirm that the original issue is fixed.
os.environ['EVENTLET_NO_GREENDNS'] = 'yes'

if debugger.enabled():
    # turn off thread patching to enable the remote debugger
    eventlet.monkey_patch(thread=False)
elif os.name == 'nt':
    # for nova-compute running on Windows(Hyper-v)
    # pipes don't support non-blocking I/O
    eventlet.monkey_patch(os=False)
else:
    eventlet.monkey_patch()

# NOTE(rpodolyaka): import oslo_service first, so that it makes eventlet hub
# use a monotonic clock to avoid issues with drifts of system time (see
# LP 1510234 for details)
# NOTE(mdbooth): This was fixed in eventlet 0.21.0. Remove when bumping
# eventlet version.
import oslo_service  # noqa
eventlet.hubs.use_hub("oslo_service:service_hub")
