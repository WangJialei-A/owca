# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import ctypes
import logging
import os

from owca import logger

LIBC = ctypes.CDLL('libc.so.6', use_errno=True)

log = logging.getLogger(__name__)

# See http://man7.org/linux/man-pages/man2/perf_event_open.2.html for details on the file and values
PARANOID_FILE = '/proc/sys/kernel/perf_event_paranoid'
ALLOW_CPU_EVENTS = 0

# The constant and enums needs to be redefined in Python as ctypes does not allow to access them
# as they are precompiler macros.
# Value: https://elixir.bootlin.com/linux/v3.10.108/source/include/uapi/linux/capability.h#L104
CAP_DAC_OVERRIDE = 2
# Value: https://elixir.bootlin.com/linux/v3.10.108/source/include/uapi/linux/capability.h#L142
CAP_SETUID = 128

# Version 3 does not seem to work and version 2 is deprecated.
# See: http://man7.org/linux/man-pages/man2/capget.2.html#DESCRIPTION
LINUX_CAPABILITY_VERSION_1 = 0x19980330

GLOBAL_ROOT_UID = 0


# We need a class that can be mapped to __user_cap_header_struct.
# See: http://man7.org/linux/man-pages/man2/capget.2.html#DESCRIPTION
class UserCapHeaderStruct(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]


# We need a class that can be mapped to __user_cap_data_struct.
# See: http://man7.org/linux/man-pages/man2/capget.2.html#DESCRIPTION
class UserCapDataStruct(ctypes.Structure):
    _fields_ = [
        ("effective", ctypes.c_uint32),
        ("permitted", ctypes.c_uint32),
        ("inheritable", ctypes.c_uint32)
    ]


class GettingCapabilitiesFailed(Exception):
    pass


def are_privileges_sufficient() -> bool:
    uid = os.geteuid()
    paranoid = _read_paranoid()
    capabilities = _get_capabilities()
    log.debug("Process capabilities: effective - {}, permitted - {}, inheritable - {}"
              .format(capabilities.effective, capabilities.permitted, capabilities.inheritable))
    has_cap_dac_override = capabilities.effective & CAP_DAC_OVERRIDE == CAP_DAC_OVERRIDE
    has_cap_setuid = capabilities.effective & CAP_SETUID == CAP_SETUID
    log.debug("Determining privileges necessary to call run OWCA - uid: {}, paranoid: {}, "
              "CAP_DAC_OVERRIDE: {}".format(uid, paranoid, has_cap_dac_override))
    return uid == GLOBAL_ROOT_UID or \
        paranoid <= ALLOW_CPU_EVENTS and has_cap_dac_override and has_cap_setuid


def _get_capabilities():
    header = UserCapHeaderStruct()
    header.pid = os.getpid()
    header.version = LINUX_CAPABILITY_VERSION_1
    data = UserCapDataStruct()
    err = LIBC.capget(ctypes.byref(header), ctypes.byref(data))
    if err != 0:
        raise GettingCapabilitiesFailed("Unable to get capabilities of {}".format(os.getpid()))
    return data


def _read_paranoid() -> int:
    with open(PARANOID_FILE, 'r') as f:
        return int(f.read())


class SetEffectiveRootUid:
    def __enter__(self):
        self.uid = os.geteuid()
        os.seteuid(0)
        log.log(logger.TRACE, "Effective user id from {} to 0".format(self.uid))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            log.warning("Exception {} with message {} thrown".format(exc_type, exc_val))
        os.seteuid(self.uid)
        log.log(logger.TRACE, "Effective user id from 0 to {}".format(self.uid))
        self.uid = 0
