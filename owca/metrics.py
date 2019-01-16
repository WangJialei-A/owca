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


from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Union


class MetricName(str, Enum):
    INSTRUCTIONS = 'instructions'
    CYCLES = 'cycles'
    CACHE_MISSES = 'cache_misses'
    CPU_USAGE_PER_CPU = 'cpu_usage_per_cpu'
    CPU_USAGE_PER_TASK = 'cpu_usage_per_task'
    MEM_BW = 'memory_bandwidth'
    LLC_OCCUPANCY = 'llc_occupancy'
    MEM_USAGE = 'memory_usage'
    MEMSTALL = 'stalls_mem_load'


class MetricType(str, Enum):
    GAUGE = 'gauge'      # arbitrary value (can go up and down)
    COUNTER = 'counter'  # monotonically increasing counter


MetricValue = Union[float, int]


# Order is enabled to allow sorting metrics according their metadata.
@dataclass(order=True)
class MetricMetadata:
    type: MetricType
    help: str


# Mapping from metric name to metrics meta data.
METRICS_METADATA: Dict[MetricName, MetricMetadata] = {
    MetricName.INSTRUCTIONS:
        MetricMetadata(
            MetricType.COUNTER,
            'Linux Perf counter for instructions per container.'),
    MetricName.CYCLES:
        MetricMetadata(
            MetricType.COUNTER,
            'Linux Perf counter for cycles per container.'),
    MetricName.CACHE_MISSES:
        MetricMetadata(
            MetricType.COUNTER,
            'Linux Perf counter for cache-misses per container.'),
    MetricName.CPU_USAGE_PER_CPU:
        MetricMetadata(
            MetricType.COUNTER,
            '[1/USER_HZ] Logical CPU usage in 1/USER_HZ (usually 10ms).'
            'Calculated using values based on /proc/stat'),
    MetricName.CPU_USAGE_PER_TASK:
        MetricMetadata(
            MetricType.COUNTER,
            '[ns] cpuacct.usage (total kernel and user space)'),
    MetricName.MEM_BW:
        MetricMetadata(
            MetricType.COUNTER,
            '[bytes] Total memory bandwidth using Memory Bandwidth Monitoring.'),
    MetricName.LLC_OCCUPANCY:
        MetricMetadata(
            MetricType.GAUGE,
            '[bytes] LLC occupancy'),
    MetricName.MEM_USAGE:
        MetricMetadata(
            MetricType.GAUGE,
            '[bytes] Total memory used by platform in bytes based on /proc/meminfo '
            'and uses heuristic based on linux free tool (total - free - buffers - cache).'
        ),
}


@dataclass
class Metric:
    name: Union[str, MetricName]
    value: MetricValue
    labels: Dict[str, str] = field(default_factory=dict)
    type: MetricType = None
    help: str = None

    @staticmethod
    def create_metric_with_metadata(name, value, labels=None):
        metric = Metric(
            name=name,
            value=value,
            labels=labels or dict()
        )
        if name in METRICS_METADATA:
            metric.type = METRICS_METADATA[name].type
            metric.help = METRICS_METADATA[name].help
        return metric


Measurements = Dict[MetricName, MetricValue]
