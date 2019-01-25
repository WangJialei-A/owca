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


from typing import List
import logging

from dataclasses import dataclass

from owca.resctrl import ResGroup
from owca.cgroups import Cgroup
from owca.perf import PerfCounters
from owca.metrics import Measurements, MetricName


log = logging.getLogger(__name__)
DEFAULT_EVENTS = (MetricName.INSTRUCTIONS, MetricName.CYCLES,
                  MetricName.CACHE_MISSES, MetricName.MEMSTALL)


def flatten_measurements(measurements: List[Measurements]):
    all_measurements_flat = dict()

    for measurement in measurements:
        assert not set(measurement.keys()) & set(all_measurements_flat.keys()), \
            'When flatting measurements the keys should not overlap!'
        all_measurements_flat.update(measurement)
    return all_measurements_flat


@dataclass
class Container:

    cgroup_path: str
    rdt_enabled: bool = True

    def __post_init__(self):
        self.cgroup = Cgroup(self.cgroup_path)
        self.perf_counters = PerfCounters(self.cgroup_path, event_names=DEFAULT_EVENTS)
        self.resgroup = ResGroup(self.cgroup_path) if self.rdt_enabled else None

    def sync(self):
        if self.rdt_enabled:
            self.resgroup.sync()

    def get_measurements(self) -> Measurements:
        try:
            return flatten_measurements([
                self.cgroup.get_measurements(),
                self.resgroup.get_measurements() if self.rdt_enabled else {},
                self.perf_counters.get_measurements(),
            ])
        except FileNotFoundError:
            log.debug('Could not read measurements for container %s. '
                      'Probably the mesos container has died during the current runner iteration.',
                      self.cgroup_path)
            # Returning empty measurements.
            return {}

    def cleanup(self):
        if self.rdt_enabled:
            self.resgroup.cleanup()
        self.perf_counters.cleanup()
