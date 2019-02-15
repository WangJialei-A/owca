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


import logging
import sys
import time
from typing import List, Dict

import colorlog

TRACE = 9
DEFAULT_MODULE = 'owca'

log = logging.getLogger(__name__)


def parse_loggers_from_list(log_levels_list: List[str]) -> Dict[str, str]:
    """Configure loggers using list of strings in a form '[module:]level'.
    """
    log_levels_dict = {}
    for log_level in log_levels_list:
        if ':' in log_level:
            if len(log_level.split(':')) != 2:
                log.error('Loggers levels from command line my be in form module:level!')
                exit(1)
            module, log_level = log_level.split(':')
        else:
            module = DEFAULT_MODULE
        log_levels_dict[module] = log_level
    return log_levels_dict


def configure_loggers_from_dict(loggers: Dict[str, str]):
    """Handle loggers section, provided as dict from module to level."""
    for module, log_level in loggers.items():
        init_logging(log_level, package_name=module)


def init_logging(level: str, package_name: str):
    level = level.upper()
    logging.captureWarnings(True)
    logging.addLevelName(TRACE, 'TRACE')
    log_colors = dict(colorlog.default_log_colors, **dict(TRACE='cyan'))

    # formatter and handler
    formatter = colorlog.ColoredFormatter(
        log_colors=log_colors,
        fmt='%(asctime)s %(log_color)s%(levelname)-8s%(reset)s'
            ' %(cyan)s{%(threadName)s} %(blue)s[%(name)s]%(reset)s %(message)s',
    )

    package_logger = logging.getLogger(package_name)
    package_logger.handlers.clear()

    # do not attache the same handler twice
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Module scoped loggers add formatter handler and disable propagation.
    package_logger.addHandler(handler)
    package_logger.propagate = False  # Because we have own handler.
    package_logger.setLevel(level)

    # Inform about tracing level (because of number of metrics).
    package_logger.log(TRACE, 'Package logger trace messages enabled.')

    # Prepare main log to be used by main entry point module
    # (because you cannot create logger before initialization).
    log.debug(
        'setting level=%s for %r package', logging.getLevelName(log.getEffectiveLevel()),
        package_name
    )


def trace(log, verbose=None):
    """Decorator to trace calling of given function reporting all arguments, returned value
    and time of executions.

    If the arguments are shown depends on 1) the level of the logger and 2) the argument
    `verbose` to the trace decorator.

    By default arguments of a decorated function are printed only if the level of the logger is
    set to TRACE.
    To force printing of input arguments at the DEBUG trace level set the verbose argument of the
    decorator to True.

    Additionally, depending on the level of the logger:
    - for DEBUG level only the name of function and execution time is logged
    - for TRACE level both arguments and return value is shown

    Example usage:

    # owca/some_module.py
    log = logging.getLogger(__name__)

    @trace(log)
    def some_function(x):
        return x+1

    some_function(1)

    output in logs (when TRACE level is used)
    [TRACE] owca.some_module: -> some_function(args=(1,), kw={})
    [TRACE] owca.some_module: <- some_function(...) = 2 (1.5s)

    output in logs (when DEBUG level is used)
    [TRACE] owca.some_module: -> some_function()
    [TRACE] owca.some_module: <- some_function() (1.5s)

    """

    def _trace(func):
        def __trace(*args, **kw):
            s = time.time()

            if verbose is not None:
                log_input_output = verbose
                level = logging.DEBUG if verbose is True else TRACE
            else:
                trace_level_is_enabled = (log.getEffectiveLevel() == TRACE)
                log_input_output = trace_level_is_enabled
                level = TRACE if trace_level_is_enabled else logging.DEBUG

            if log_input_output:
                log.log(level, '-> %s(args=%r, kw=%r)', func.__name__, args, kw)
            else:
                log.log(level, '-> %s()', func.__name__)

            rv = func(*args, **kw)

            if log_input_output:
                log.log(level, '<- %s() = %r (%.2fs)', func.__name__, rv, time.time() - s)
            else:
                log.log(level, '<- %s() (%.2fs)', func.__name__, time.time() - s)

            return rv

        return __trace

    return _trace
