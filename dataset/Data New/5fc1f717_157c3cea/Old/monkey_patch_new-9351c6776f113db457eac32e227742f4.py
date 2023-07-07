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
from oslo_utils import importutils
from six.moves import reload_module

# NOTE(mdbooth): Imports only sys (2019-01-30). Other modules imported at
# runtime on execution of debugger.init().
from nova import debugger

if debugger.enabled():
    # turn off thread patching to enable the remote debugger
    eventlet.monkey_patch(thread=False)
elif os.name == 'nt':
    # for nova-compute running on Windows(Hyper-v)
    # pipes don't support non-blocking I/O
    eventlet.monkey_patch(os=False)
else:
    eventlet.monkey_patch()

# NOTE(rgerganov): oslo.context is storing a global thread-local variable
# which keeps the request context for the current thread. If oslo.context
# is imported before calling monkey_patch(), then this thread-local won't
# be green. To workaround this, reload the module after calling
# monkey_patch()
# NOTE(mdbooth): Is this still true? If so, can we avoid it?
reload_module(importutils.import_module('oslo_context.context'))
