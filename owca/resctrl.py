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


import errno
import logging
import os

from owca import logger
from owca.cgroups import BASE_SUBSYSTEM_PATH
from owca.metrics import Measurements, MetricName
from owca.security import SetEffectiveRootUid

BASE_RESCTRL_PATH = '/sys/fs/resctrl'
MON_GROUPS = 'mon_groups'
TASKS_FILENAME = 'tasks'
SCHEMATA = 'schemata'
INFO = 'info'
MON_DATA = 'mon_data'
MON_L3_00 = 'mon_L3_00'
MBM_TOTAL = 'mbm_total_bytes'
LLC_OCCUPANCY = 'llc_occupancy'


log = logging.getLogger(__name__)


def cleanup_resctrl():
    """Remove taskless subfolders at resctrl folders to free scarce CLOS and RMID resources. """

    def _clean_taskless_folders(initialdir, subfolder, resource_recycled):
        for entry in os.listdir(os.path.join(initialdir, subfolder)):
            # Path to folder e.g. mesos-xxx represeting running container.
            directory_path = os.path.join(BASE_RESCTRL_PATH, subfolder, entry)
            # Only examine folders at first level.
            if os.path.isdir(directory_path):
                # Examine tasks file
                resctrl_tasks_path = os.path.join(directory_path, TASKS_FILENAME)
                tasks = ''
                if not os.path.exists(resctrl_tasks_path):
                    # Skip metadata folders e.g. info.
                    continue
                with open(resctrl_tasks_path) as f:
                    tasks += f.read()
                if len(tasks.split()) == 0:
                    log.warning('Found taskless (empty) mon group at %r - recycle %s resource.'
                                % (directory_path, resource_recycled))
                    log.log(logger.TRACE, 'resctrl (mon_groups) - cleanup: rmdir(%s)',
                            directory_path)
                    os.rmdir(directory_path)

    # Remove all monitoring groups for both CLOS and RMID.
    _clean_taskless_folders(BASE_RESCTRL_PATH, '', resource_recycled='CLOS')
    _clean_taskless_folders(BASE_RESCTRL_PATH, MON_GROUPS, resource_recycled='RMID')


def check_resctrl():
    """
    :return: True if resctrl is mounted and has required file
             False if resctrl is not mounted or required file is missing
    """
    run_anyway_text = 'If you wish to run script anyway,' \
                      'please set rdt_enabled to False in configuration file.'

    resctrl_tasks = os.path.join(BASE_RESCTRL_PATH, TASKS_FILENAME)
    try:
        with open(resctrl_tasks):
            pass
    except IOError as e:
        log.debug('Error: Failed to open %s: %s', resctrl_tasks, e)
        log.critical('Resctrl not mounted. ' + run_anyway_text)
        return False

    mon_data = os.path.join(BASE_RESCTRL_PATH, MON_DATA, MON_L3_00, MBM_TOTAL)
    try:
        with open(mon_data):
            pass
    except IOError as e:
        log.debug('Error: Failed to open %s: %s', mon_data, e)
        log.critical('Resctrl does not support Memory Bandwidth Monitoring.' +
                     run_anyway_text)
        return False

    return True


class ResGroup:

    def __init__(self, cgroup_path):
        assert cgroup_path.startswith('/'), 'Provide cgroup_path with leading /'
        relative_cgroup_path = cgroup_path[1:]  # cgroup path without leading '/'
        self.cgroup_fullpath = os.path.join(
            BASE_SUBSYSTEM_PATH, relative_cgroup_path)
        # Resctrl group is flat so flatten then cgroup hierarchy.
        flatten_rescgroup_name = relative_cgroup_path.replace('/', '-')
        self.resgroup_dir = os.path.join(BASE_RESCTRL_PATH, MON_GROUPS, flatten_rescgroup_name)
        self.resgroup_tasks = os.path.join(self.resgroup_dir, TASKS_FILENAME)

    def sync(self, max_attempts=3):
        """Copy all the tasks from all cgroups to resctrl tasks file
        """
        if not os.path.exists('/sys/fs/resctrl'):
            log.warning('Resctrl not mounted, ignore sync!')
            return

        attempt = 1
        while attempt <= max_attempts:
            tasks = ''
            with open(os.path.join(self.cgroup_fullpath, TASKS_FILENAME)) as f:
                tasks += f.read()
            log.log(logger.TRACE, 'sync: Read tasks for %r (found %d pids)'
                    % (self.resgroup_dir, len(tasks)))

            try:
                log.log(logger.TRACE, 'resctrl: makedirs(%s)', self.resgroup_dir)
                os.makedirs(self.resgroup_dir, exist_ok=True)
            except OSError as e:
                if e.errno == errno.ENOSPC:  # "No space left on device"
                    raise Exception("Limit of workloads reached! (Oot of available CLoSes/RMIDs!)")
                raise

            try:
                log.log(logger.TRACE, 'sync: Writings tasks for %r' % (self.resgroup_dir))
                with open(self.resgroup_tasks, 'w') as f:
                    with SetEffectiveRootUid():
                        for task in tasks.split():
                            f.write(task)
                            f.flush()
            except ProcessLookupError:
                log.warning('Could not write process pids to resctrl (%r). '
                            'Process probably does not exist. '
                            'Restarting synchronization (attempt=%d).'
                            % (self.resgroup_dir, attempt))
                attempt += 1
                continue

            log.log(logger.TRACE,
                    'sync: Succesful synchronization for %r - braking' % self.resgroup_dir)
            break

        else:
            log.warning('sync: Unsuccessful synchronization attempts. Ignoring.')
            return

        log.log(logger.TRACE,
                'sync: Succesful synchronization for %r - returning' % self.resgroup_dir)

    def get_measurements(self) -> Measurements:
        """
        mbm_total: Memory bandwidth - type: counter, unit: [bytes]
        :return: Dictionary containing memory bandwidth
        and cpu usage measurements
        """
        mbm_total = 0
        llc_occupancy = 0

        # mon_dir contains event files for specific socket:
        # llc_occupancy, mbm_total_bytes, mbm_local_bytes
        for mon_dir in os.listdir(os.path.join(self.resgroup_dir, MON_DATA)):
            with open(os.path.join(self.resgroup_dir, MON_DATA,
                                   mon_dir, MBM_TOTAL)) as mbm_total_file:
                mbm_total += int(mbm_total_file.read())
            with open(os.path.join(self.resgroup_dir, MON_DATA,
                                   mon_dir, LLC_OCCUPANCY)) as llc_occupancy_file:
                llc_occupancy += int(llc_occupancy_file.read())

        return {MetricName.MEM_BW: mbm_total, MetricName.LLC_OCCUPANCY: llc_occupancy}

    def cleanup(self):
        try:
            log.log(logger.TRACE, 'cleanup: rmdir(%s)', self.resgroup_dir)
            os.rmdir(self.resgroup_dir)
        except FileNotFoundError:
            log.debug('cleanup: directory already does not exist %s', self.resgroup_dir)
