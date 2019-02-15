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

from io import TextIOWrapper
from typing import List, Dict
import re
from owca.metrics import Metric, MetricType
from owca.wrapper import wrapper_main
from owca.wrapper.parser import readline_with_check

EOF_line = "..."


def parse(input: TextIOWrapper, regexp: str, separator: str = None,
          labels: Dict[str, str] = {}, metric_name_prefix: str = '') -> List[Metric]:
    """Custom parse function for stress_ng
        stress-ng: info:  [99] Time 1546433449, counter=173
        stress-ng: info:  [96] Time 1546433449, counter=210
        stress-ng: info:  [103] Time 1546433449, counter=191
        stress-ng: info:  [104] Time 1546433449, counter=195
        stress-ng: info:  [106] Time 1546433449, counter=197
        stress-ng: info:  [101] Time 1546433450, counter=250
        stress-ng: info:  [98] Time 1546433450, counter=261
        stress-ng: info:  [97] Time 1546433450, counter=273
        stress-ng: info:  [99] Time 1546433450, counter=217
        stress-ng: info:  [96] Time 1546433450, counter=263
        stress-ng: info:  [113] stress-ng-stream: memory rate: 1806.87 MB/sec, 722.75 Mflop/sec
        stress-ng: info:  [114] Time 1546433537, counter=304
        stress-ng: info:  [115] Time 1546433537, counter=282
        stress-ng: info:  [119] stress-ng-stream: memory rate: 1742.69 MB/sec, 697.07 Mflop/sec
        stress-ng: info:  [117] stress-ng-stream: memory rate: 1999.33 MB/sec, 799.73 Mflop/sec
        stress-ng: info:  [115] stress-ng-stream: memory rate: 1922.38 MB/sec, 768.95 Mflop/sec
        stress-ng: info:  [114] stress-ng-stream: memory rate: 2067.34 MB/sec, 826.94 Mflop/sec
        stress-ng: info:  [121] stress-ng-stream: memory rate: 1849.08 MB/sec, 739.63 Mflop/sec
        stress-ng: info:  [123] stress-ng-stream: memory rate: 1848.92 MB/sec, 739.57 Mflop/sec
        stress-ng: info:  [116] stress-ng-stream: memory rate: 2027.03 MB/sec, 810.81 Mflop/sec
        stress-ng: info:  [112] successful run completed in 6.02s
        ---
        system-info:
              stress-ng-version: 0.09.28
              run-by: root
              date-yyyy-mm-dd: 2019:01:02
              time-hh-mm-ss: 12:52:17
              epoch-secs: 1546433537
              hostname: d4840a594b43
              sysname: Linux
              nodename: d4840a594b43
              release: 4.15.0-43-generic
              version: #46-Ubuntu SMP Thu Dec 6 14:45:28 UTC 2018
              machine: x86_64
              uptime: 6933
              totalram: 33605246976
              freeram: 10913120256
              sharedram: 1651642368
              bufferram: 649097216
              totalswap: 34233905152
              freeswap: 34233905152
              pagesize: 4096
              cpus: 8
              cpus-online: 8
              ticks-per-second: 100

        stress-ng: info:  [112] stressor       bogo ops real time  usr time  sys time   bogo ops/s /
        bogo ops/s
        stress-ng: info:  [112]                           (secs)    (secs)    (secs)   (real time) /
        (usr+sys time)
        metrics:
        stress-ng: info:  [112] stream             2250      6.01     40.81      0.39       374.12 /
        54.61
            - stressor: stream
              bogo-ops: 2250
              bogo-ops-per-second-usr-sys-time: 54.611650
              bogo-ops-per-second-real-time: 374.121510
              wall-clock-time: 6.014089
              user-time: 40.810000
              system-time: 0.390000

        ...
    """

    new_metrics = []
    new_line = readline_with_check(input, EOF_line)

    # Parse metric summary on the end stressing
    brief = re.search(
        r'(?P<bogo_ops>\d+.\d*) +'
        r'(?P<real_time>\d+.\d*) +'
        r'(?P<user_time>\d+.\d*) +'
        r'(?P<system_time>\d+.\d*) +'
        r'(?P<bogo_ops_per_second_real_time>\d+.\d*) +'
        r'(?P<bogo_ops_per_second_usr_sys_time>\d+.\d*)',
        new_line)
    if brief is not None:
        bogo_ops = float(brief['bogo_ops'])
        real_time = float(brief['real_time'])
        user_time = float(brief['user_time'])
        system_time = float(brief['system_time'])
        bogo_ops_real = float(brief['bogo_ops_per_second_real_time'])
        bogo_ops_usr_sys = float(brief['bogo_ops_per_second_usr_sys_time'])

        new_metrics.append(
            Metric(metric_name_prefix + 'bogo_ops', bogo_ops,
                   type=MetricType.GAUGE, labels=labels,
                   help="Summary bogo ops"))
        new_metrics.append(
            Metric(metric_name_prefix + 'real_time', real_time,
                   type=MetricType.GAUGE, labels=labels,
                   help="Summary real_time (secs)"))
        new_metrics.append(
            Metric(metric_name_prefix + 'user_time', user_time,
                   type=MetricType.GAUGE, labels=labels,
                   help="Summary user_time (secs)"))
        new_metrics.append(
            Metric(metric_name_prefix + 'system_time', system_time,
                   type=MetricType.GAUGE, labels=labels,
                   help="Summary system_time (secs)"))
        new_metrics.append(
            Metric(metric_name_prefix + 'bogo_ops_per_second_real_time', bogo_ops_real,
                   type=MetricType.GAUGE, labels=labels,
                   help="Summary bogo ops/s real time"))
        new_metrics.append(
            Metric(metric_name_prefix + 'bogo_ops_per_second_usr_sys_time', bogo_ops_usr_sys,
                   type=MetricType.GAUGE, labels=labels,
                   help="Summary bogo ops/s usr+sys time"))

    info = re.search(r'stress-ng: info: {2}\[(?P<id>\d*)\]+ ' +
                     r'Time (?P<time>\d*), counter=(?P<counter>\d*)', new_line)

    if info is not None:
        id_proc = info['id']
        counter = int(info['counter'])

        labels.update({"id_proc_stress_ng": id_proc})

        new_metrics.append(
            Metric(metric_name_prefix + 'bogo_ops_counter', counter,
                   type=MetricType.COUNTER, labels=labels,
                   help="Counter bogo ops per proc stress-ng, updated per 1 sec"))

    return new_metrics


if __name__ == "__main__":
    wrapper_main.main(parse)
