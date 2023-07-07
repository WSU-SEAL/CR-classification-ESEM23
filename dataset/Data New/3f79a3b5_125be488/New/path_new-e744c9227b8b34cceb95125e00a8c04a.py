# Copyright 2016 Red Hat, Inc
# Copyright 2017 Rackspace Australia
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

"""Routines that bypass file-system checks."""

import errno
import os

from oslo_utils import fileutils

from nova import exception
import nova.privsep


@nova.privsep.sys_admin_pctxt.entrypoint
def readfile(path):
    if not os.path.exists(path):
        raise exception.FileNotFound(file_path=path)
    with open(path, 'r') as f:
        return f.read()


@nova.privsep.sys_admin_pctxt.entrypoint
def writefile(path, mode, content):
    if not os.path.exists(path):
        raise exception.FileNotFound(file_path=path)
    with open(path, mode) as f:
        f.write(content)


@nova.privsep.sys_admin_pctxt.entrypoint
def readlink(path):
    if not os.path.exists(path):
        raise exception.FileNotFound(file_path=path)
    return os.readlink(path)


@nova.privsep.sys_admin_pctxt.entrypoint
def chown(path, uid=-1, gid=-1):
    if not os.path.exists(path):
        raise exception.FileNotFound(file_path=path)
    return os.chown(path, uid, gid)


@nova.privsep.sys_admin_pctxt.entrypoint
def makedirs(path):
    fileutils.ensure_tree(path)


@nova.privsep.sys_admin_pctxt.entrypoint
def chmod(path, mode):
    if not os.path.exists(path):
        raise exception.FileNotFound(file_path=path)
    os.chmod(path, mode)


@nova.privsep.sys_admin_pctxt.entrypoint
def utime(path):
    if not os.path.exists(path):
        raise exception.FileNotFound(file_path=path)
    # context wrapper ensures the file exists before trying to modify time
    # which fixes a race condition with NFS image caching (see LP#1809123)
    with open(path, 'a'):
        os.utime(path, None)


@nova.privsep.sys_admin_pctxt.entrypoint
def rmdir(path):
    if not os.path.exists(path):
        raise exception.FileNotFound(file_path=path)
    os.rmdir(path)


class path(object):
    @staticmethod
    @nova.privsep.sys_admin_pctxt.entrypoint
    def exists(path):
        return os.path.exists(path)


@nova.privsep.sys_admin_pctxt.entrypoint
def last_bytes(path, num):
    # NOTE(mikal): this is implemented in this contrived manner because you
    # can't mock a decorator in python (they're loaded at file parse time,
    # and the mock happens later).
    with open(path, 'rb') as f:
        return _last_bytes_inner(f, num)


def _last_bytes_inner(file_like_object, num):
    """Return num bytes from the end of the file, and remaining byte count.

    :param file_like_object: The file to read
    :param num: The number of bytes to return

    :returns: (data, remaining)
    """

    try:
        file_like_object.seek(-num, os.SEEK_END)
    except IOError as e:
        # seek() fails with EINVAL when trying to go before the start of
        # the file. It means that num is larger than the file size, so
        # just go to the start.
        if e.errno == errno.EINVAL:
            file_like_object.seek(0, os.SEEK_SET)
        else:
            raise

    remaining = file_like_object.tell()
    return (file_like_object.read(), remaining)
