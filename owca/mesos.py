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


from dataclasses import dataclass, field
from typing import Dict, List, Union
import urllib.parse
import logging
import os

import requests

# Mesos tasks id
from owca.nodes import Node, TaskId
from owca.metrics import Measurements, Metric


MESOS_TASK_STATE_RUNNING = 'TASK_RUNNING'
CGROUP_DEFAULT_SUBSYSTEM = 'cpu'

log = logging.getLogger(__name__)


@dataclass
class MesosTask:  # implements nodes.Task but abstractclasses cannot be implemented by dataclasses

    name: str

    executor_pid: int
    container_id: str  # Mesos containerizer identifier "ID used to uniquely identify a container"
    task_id: TaskId  # Mesos-level task identifier

    # for debugging purposes
    executor_id: str
    agent_id: str

    # inferred
    cgroup_path: str  # Starts with leading "/"
    labels: Dict[str, str] = field(default_factory=dict)

    # Resources assigned accorind Mesos/Aurora task definition.
    resources: Dict[str, float] = field(default_factory=dict)

    def __hash__(self):
        """Every instance of mesos task is uniqully identified by cgroup_path.
        Assumption here is that every mesos task is represented by one main cgroup.
        """
        return id(self.cgroup_path)


def find_cgroup(pid):
    """ Returns cgroup_path relative to 'cpu' subsystem based on /proc/{pid}/cgroup
    with leading '/'"""

    with open(f'/proc/{pid}/cgroup') as f:
        for line in f:
            _, subsystems, path = line.strip().split(':')
            subsystems = subsystems.split(',')
            if CGROUP_DEFAULT_SUBSYSTEM in subsystems:
                return path
        else:
            raise Exception(f'Cannot find cgroup mesos path for {pid}')


@dataclass
class MesosNode(Node):

    mesos_agent_endpoint: str = 'https://127.0.0.1:5051'
    ssl_verify: Union[bool, str] = True  # requests: Can be used to pass cert CA bundle.

    METHOD = 'GET_STATE'
    api_path = '/api/v1'

    def __post_init__(self):
        if isinstance(self.ssl_verify, str):
            if not os.path.exists(self.ssl_verify):
                raise FileNotFoundError('cannot locate CA cert bundle file at %s for '
                                        'verify SSL Mesos connection!' % self.ssl_verify)

    def get_tasks(self):
        """ only return running tasks """
        full_url = urllib.parse.urljoin(self.mesos_agent_endpoint, self.api_path)
        r = requests.post(
            full_url,
            json=dict(type=self.METHOD),
            verify=self.ssl_verify
        )
        r.raise_for_status()
        state = r.json()
        tasks = []

        # Fast return path if there is no any launched tasks.
        if 'launched_tasks' not in state['get_state']['get_tasks']:
            return []

        for launched_task in state['get_state']['get_tasks']['launched_tasks']:
            if 'statuses' not in launched_task or not len(launched_task['statuses']):
                continue

            statuses = launched_task['statuses']
            last_status = statuses[-1]  # Assume the last on is the latest state # TODO: confirm
            if last_status['state'] != MESOS_TASK_STATE_RUNNING:
                continue

            if 'executor_pid' not in last_status['container_status']:
                log.warning("'executor_pid' not found in container status for task %s on agent %s",
                            last_status['task_id']['value'],
                            last_status['agent_id']['value'])
                continue

            executor_pid = last_status['container_status']['executor_pid']
            cgroup_path = find_cgroup(executor_pid)

            labels = {label['key']: label['value'] for label in launched_task['labels']['labels']}

            # Extract scalar resoruces.
            resources = dict()
            for resource in launched_task['resources']:
                if resource['type'] == 'SCALAR':
                    resources[resource['name']] = float(resource['scalar']['value'])

            tasks.append(
                MesosTask(
                    name=launched_task['name'],
                    executor_pid=executor_pid,
                    cgroup_path=cgroup_path,
                    container_id=last_status['container_status']['container_id']['value'],
                    task_id=last_status['task_id']['value'],
                    agent_id=last_status['agent_id']['value'],
                    executor_id=last_status['executor_id']['value'],
                    labels=labels,
                    resources=resources
                )
            )

        return tasks


MESOS_LABELS_PREFIXES_TO_DROP = ('org.apache.', 'aurora.metadata.')


def sanitize_mesos_label(label_key):
    """Removes unwanted prefixes from Aurora & Mesos e.g. 'org.apache.aurora'
    and replaces invalid characters like "." with underscore.
    """
    # Drop unwanted prefixes
    for unwanted_prefix in MESOS_LABELS_PREFIXES_TO_DROP:
        if label_key.startswith(unwanted_prefix):
            label_key = label_key.replace(unwanted_prefix, '')

    # Prometheus labels cannot contain ".".
    label_key = label_key.replace('.', '_')

    return label_key


def create_metrics(task_measurements: Measurements) -> List[Metric]:
    """Prepare a list of metrics for a mesos tasks based on provided measurements
    applying common_labels.
    :param task_measurements: use values of measurements to create metrics
    """
    metrics = []
    for metric_name, metric_value in task_measurements.items():
        metric = Metric.create_metric_with_metadata(name=metric_name, value=metric_value)
        metrics.append(metric)
    return metrics
