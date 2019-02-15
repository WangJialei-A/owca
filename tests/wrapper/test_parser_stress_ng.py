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


from io import StringIO

from owca.metrics import Metric, MetricType
from owca.wrapper.parser_stress_ng import parse


def test_parse():
    data = """
        stress-ng: info:  [99] Time 1546433449, counter=173
        stress-ng: info:  [96] Time 1546433449, counter=210
        stress-ng: info:  [103] Time 1546433449, counter=191
        stress-ng: info:  [104] Time 1546433449, counter=195
    """

    number_of_reads = len(data.splitlines())
    input_ = StringIO(data)

    got = []
    for _ in range(number_of_reads):
        got.extend(parse(input_, '', None, {}, 'stress_ng_'))
    expected = [
        Metric('stress_ng_bogo_ops_counter', value=173, labels={'id_proc_stress_ng': '99'},
               type=MetricType.COUNTER,
               help="Counter bogo ops per proc stress-ng, updated per 1 sec"),
        Metric('stress_ng_bogo_ops_counter', value=210, labels={'id_proc_stress_ng': '96'},
               type=MetricType.COUNTER,
               help="Counter bogo ops per proc stress-ng, updated per 1 sec"),
        Metric('stress_ng_bogo_ops_counter', value=191, labels={'id_proc_stress_ng': '103'},
               type=MetricType.COUNTER,
               help="Counter bogo ops per proc stress-ng, updated per 1 sec"),
        Metric('stress_ng_bogo_ops_counter', value=195, labels={'id_proc_stress_ng': '104'},
               type=MetricType.COUNTER,
               help="Counter bogo ops per proc stress-ng, updated per 1 sec")
    ]

    assert expected == got


def test_parse_end_stress():

    data = """
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

        stress-ng: info:  [112] stressor       bogo ops real time  usr time  sys time   bogo ops/s \
        bogo ops/s
        stress-ng: info:  [112]                           (secs)    (secs)    (secs)   (real time) \
        (usr+sys time)
        metrics:
        stress-ng: info:  [112] stream             2250      6.01     40.81      0.39       374.12 \
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

    number_of_reads = len(data.splitlines())
    input_ = StringIO(data)

    got = []
    for _ in range(number_of_reads):
        got.extend(parse(input_, '', None, {}, 'stress_ng_'))
    expected = [
        Metric('stress_ng_bogo_ops', value=2250, labels={},
               type=MetricType.GAUGE, help="Summary bogo ops"),
        Metric('stress_ng_real_time', value=6.01, labels={},
               type=MetricType.GAUGE, help="Summary real_time (secs)"),
        Metric('stress_ng_user_time', value=40.81, labels={},
               type=MetricType.GAUGE, help="Summary user_time (secs)"),
        Metric('stress_ng_system_time', value=0.39, labels={},
               type=MetricType.GAUGE, help="Summary system_time (secs)"),
        Metric('stress_ng_bogo_ops_per_second_real_time', value=374.12, labels={},
               type=MetricType.GAUGE, help="Summary bogo ops/s real time"),
        Metric('stress_ng_bogo_ops_per_second_usr_sys_time', value=54.61, labels={},
               type=MetricType.GAUGE, help="Summary bogo ops/s usr+sys time")
    ]

    assert expected == got
