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
import struct
from typing import List, Dict, BinaryIO

from owca import perf_const as pc
from owca import logger
from owca.metrics import Measurements, MetricName
from owca.security import SetEffectiveRootUid

LIBC = ctypes.CDLL('libc.so.6', use_errno=True)

log = logging.getLogger(__name__)


def _get_cpu_model() -> pc.CPUModel:
    with SetEffectiveRootUid():
        with open("/dev/cpu/0/cpuid", "rb") as f:
            b = f.read(32)
            eax = int(b[16]) + (int(b[17]) << 8) + (int(b[18]) << 16) + (int(b[19]) << 24)
            log.log(logger.TRACE, '16,17,18,19th bytes from /dev/cpu/0/cpuoid: %b %b %b %b',
                    b[16], b[17], b[18], b[19])
            model = (eax >> 4) & 0xF
            family = (eax >> 8) & 0xF
            extended_model = (eax >> 16) & 0xF
            extended_family = (eax >> 20) & 0xFF
            display_family = family
            if family == 0xF:
                display_family += extended_family
            display_model = model
            if family == 0x6 or family == 0xF:
                display_model += (extended_model << 4)
            if display_model in [0x4E, 0x5E, 0x55]:
                return pc.CPUModel.SKYLAKE
            elif display_model in [0x3D, 0x47, 0x4F, 0x56]:
                return pc.CPUModel.BROADWELL
            else:
                return pc.CPUModel.UNKNOWN


def _get_memstall_config() -> int:
    model = _get_cpu_model()
    event, umask, cmask = (0, 0, 0)
    if model == pc.CPUModel.SKYLAKE:
        event, umask, cmask = (0xA3, 0x14, 20)
    elif model == pc.CPUModel.BROADWELL:
        event, umask, cmask = (0xA3, 0x06, 6)
    elif model == pc.CPUModel.UNKNOWN:
        event, umask, cmask = (0, 0, 0)
    return event | (umask << 8) | (cmask << 24)


def _get_online_cpus() -> List[int]:
    """Return list with numbers of online cores for current machine"""
    online_cpus = []
    with open('/sys/devices/system/cpu/online', 'r') as fobj:
        online_cpus = _parse_online_cpus_string(fobj.read())
    return online_cpus


def _parse_online_cpus_string(raw_string) -> List[int]:
    """
    Parses string returned by /sys/devices/system/cpu/online
    and returns a list of online cores
    """
    parsed_cpus_info = []
    for nr in raw_string.split(','):
        if '-' not in nr:
            parsed_cpus_info.append(int(nr))
        else:
            start, end = nr.split('-')
            parsed_cpus_info.extend(range(int(start), int(end) + 1))
    return parsed_cpus_info


def _parse_event_groups(file, event_names) -> Measurements:
    """Reads event values from the event file"""
    measurements = {}
    size = struct.unpack('q', file.read(8))[0]
    assert size == len(event_names)
    time_enabled = struct.unpack('q', file.read(8))[0]
    time_running = struct.unpack('q', file.read(8))[0]
    for current_event in range(0, size):
        raw_value = struct.unpack('q', file.read(8))[0]
        measurements[event_names[current_event]] = _scale_counter_value(
            raw_value,
            time_enabled,
            time_running
        )
        # id is unused, but we still need to read the whole struct
        struct.unpack('q', file.read(8))[0]
    return measurements


def _aggregate_measurements(measurements_per_cpu, event_names) -> Measurements:
    """Sums measurements values from all cpus"""
    aggregated_measurements: Measurements = {metric_name: 0 for metric_name in event_names}
    for cpu, measurements_from_single_cpu in measurements_per_cpu.items():
        for metric_name, metric_value in measurements_from_single_cpu.items():
            aggregated_measurements[metric_name] += metric_value
    return aggregated_measurements


def _perf_event_open(perf_event_attr, pid, cpu, group_fd, flags) -> int:
    """Wrapper on perf_event_open function using libc syscall"""
    return LIBC.syscall(pc.PERF_EVENT_OPEN_NR, perf_event_attr, pid, cpu,
                        group_fd, flags)


def _get_cgroup_fd(cgroup) -> int:
    """
    Return FD for provided cgroup
    """
    path = os.path.join('/sys/fs/cgroup/perf_event', cgroup)
    # cgroup is a directory, so we can't use fdopen on the file
    # descriptor we receive from os.open
    return os.open(path, os.O_RDONLY)


def _scale_counter_value(raw_value, time_enabled, time_running) -> float:
    """
    Scales raw counter measurement with time_enabled and time_running values,
    according to https://perf.wiki.kernel.org/index.php/Tutorial#multiplexing_and_scaling_events
    """
    # After the start of measurement, first few readings may contain only 0's
    if time_running == 0:
        return 0.0
    if time_enabled == 0:
        log.warning("Event time enabled equals 0")
        return 0.0
    if time_running != time_enabled:
        scaling_rate = float(time_enabled) / float(time_running)
        log.warning(f'Measurement scaling rate: {scaling_rate}')
        return round(float(raw_value) * scaling_rate)
    else:
        return float(raw_value)


def _create_event_attributes(event_name, disabled):
    """Creates perf_event_attr structure for perf_event_open syscall"""
    attr = pc.PerfEventAttr()
    attr.size = pc.PERF_ATTR_SIZE_VER5
    if event_name == MetricName.MEMSTALL:
        attr.type = pc.PerfType.PERF_TYPE_RAW
        attr.config = _get_memstall_config()
    else:
        attr.type = pc.PerfType.PERF_TYPE_HARDWARE
        attr.config = pc.HardwareEventNameMap[event_name]
    attr.sample_type = pc.PERF_SAMPLE_IDENTIFIER
    attr.read_format = (pc.PERF_FORMAT_GROUP |
                        pc.PERF_FORMAT_TOTAL_TIME_ENABLED |
                        pc.PERF_FORMAT_TOTAL_TIME_RUNNING |
                        pc.PERF_FORMAT_ID)

    attr.flags = pc.AttrFlags.exclude_guest

    if disabled:
        attr.flags |= pc.AttrFlags.disabled

    return attr


def _create_file_from_fd(pfd):
    """Validates file description and creates a file-like object"""
    # -1 is returned on error: http://man7.org/linux/man-pages/man2/open.2.html#RETURN_VALUE
    if pfd == -1:
        errno = ctypes.get_errno()
        raise UnableToOpenPerfEvents('Invalid perf event file descriptor: {}, {}'
                                     .format(errno, os.strerror(errno)))
    return os.fdopen(pfd, 'rb')


class PerfCounters:
    """Perf facade on perf_event_open system call"""

    def __init__(self, cgroup_path: str, event_names: List[MetricName]):
        # Provide cgroup_path with leading '/'
        assert cgroup_path.startswith('/')
        # cgroup path without leading '/'
        relative_cgroup_path = cgroup_path[1:]
        self._cgroup_fd: int = _get_cgroup_fd(relative_cgroup_path)

        # all perf file descriptors, except leaders
        self._event_files: List[BinaryIO] = []
        # perf data file descriptors (only leaders) per cpu
        self._group_event_leader_files: Dict[int, BinaryIO] = {}

        # keep event names for output information
        self._event_names: List[MetricName] = event_names
        # DO the magic and enabled everything + start counting
        self._open()

    def get_measurements(self) -> Measurements:
        return self._read_events()

    def cleanup(self):
        """Closes all opened file descriptors"""
        for file in self._group_event_leader_files.values():
            file.close()
        for file in self._event_files:
            file.close()
        # _cgroup_fd is an int, thus we need to close it with os.close
        os.close(self._cgroup_fd)

    def _open_for_cpu(self, cpu, event_name):
        """Opens file descriptor for event selected via event_name, for selected cpu"""
        group_file = self._group_event_leader_files.get(cpu)
        is_group_leader = group_file is None

        # man perf_event_open cite regarding the disabled variable:
        #   When creating an event group, typically the group leader is
        #     initialized with disabled set to 1 and any child events are
        #     initialized with disabled set to 0.  Despite disabled being 0,
        #     the child events will not start until the group leader is
        #     enabled.
        # Disabled when creating new leader.
        # Enabled for children

        # man perf_event_open cite regarding group_fd variable:
        #       The cgroup is identified by passing a file descriptor opened
        #       on its directory in the cgroupfs filesystem.  For instance, if
        #       the cgroup to monitor is called test, then a file descriptor
        #       opened on /dev/cgroup/test (assuming cgroupfs is mounted on
        #       /dev/cgroup) must be passed as the pid parameter.  cgroup
        #       monitoring is available only for system-wide events and may
        #       therefore require extra permissions.
        if is_group_leader:
            disabled = True
            pid = self._cgroup_fd
            flags = pc.PERF_FLAG_PID_CGROUP | pc.PERF_FLAG_FD_CLOEXEC
            group_fd = -1
        else:
            disabled = False
            pid = -1
            flags = pc.PERF_FLAG_FD_CLOEXEC
            group_fd = group_file.fileno()

        self.attr = _create_event_attributes(event_name, disabled=disabled)

        pfd = _perf_event_open(perf_event_attr=ctypes.byref(self.attr),
                               pid=pid,
                               cpu=cpu,
                               group_fd=group_fd,
                               flags=flags)
        perf_event_file = _create_file_from_fd(pfd)

        if is_group_leader:
            self._group_event_leader_files[cpu] = perf_event_file
        else:
            self._event_files.append(perf_event_file)

    def _open(self):
        """Opens file descriptors for selected events, for all online cpus"""
        for event_name in self._event_names:
            for cpu in _get_online_cpus():
                self._open_for_cpu(cpu, event_name)
        self._reset_and_enable_group_event_leaders()

    def _reset_and_enable_group_event_leaders(self):
        for group_event_leader_file in self._group_event_leader_files.values():
            if LIBC.ioctl(group_event_leader_file.fileno(), pc.PERF_EVENT_IOC_RESET, 0) < 0:
                raise OSError("Cannot reset perf counts")
            if LIBC.ioctl(group_event_leader_file.fileno(), pc.PERF_EVENT_IOC_ENABLE, 0) < 0:
                raise OSError("Cannot enable perf counts")

    def _read_events(self) -> Measurements:
        """Reads, scales and aggregates event measurements"""
        scaled_measurements_per_cpu: Dict[int, Measurements] = {}
        for cpu, event_leader_file in self._group_event_leader_files.items():
            scaled_measurements_per_cpu[cpu] = _parse_event_groups(event_leader_file,
                                                                   self._event_names)

        return _aggregate_measurements(scaled_measurements_per_cpu, self._event_names)


class UnableToOpenPerfEvents(Exception):
    pass
