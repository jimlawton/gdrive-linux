#!/usr/bin/env python
#
# Copyright 2012 Jim Lawton. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, sys, time, logging

import daemon
from gdocs import Session
from drive_config import DriveConfig

UPDATE_INTERVAL = 30    # Sync update interval in seconds.

class DriveDaemon(daemon.Daemon, object):
    "Google Drive daemon class."

    def __init__(self):
        "Class constructor."
        config = DriveConfig()
        pidfile = config.getPidFile()
        loglevel = config.getLogLevel()
        logfile = config.getLogFile()
        super(DriveDaemon, self).__init__(pidfile, loglevel, logfile)

    def run(self):
        "Run the daemon."
        logging.debug("Creating session...")
        session = Session(logger=self._logger)
        if session == None:
            sys.exit("Error, could not create Google Docs session!")
        
        while True:
            logging.debug("Daemon poll loop...")
            # TODO: Add sync logic.
            # TODO: How do we detect that a sync is ongoing, and skip?
            # Maybe have a queue of sync/update operations, and use a 
            # single (initially anyway) thread to process them.
            time.sleep(UPDATE_INTERVAL)
            
        logging.debug("Daemon exiting...")
