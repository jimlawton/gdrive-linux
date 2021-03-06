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

# This code is part of gdrive-linux (https://code.google.com/p/gdrive-linux/).

import os, sys, time, logging

from gdata.client import Error

import daemon
from gdocs import Session
from drive_config import DriveConfig

UPDATE_INTERVAL = 30    # Sync update interval in seconds.
RETRY_INTERVAL = 60     # Retry interval in seconds.

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
            try:
                session.update(download=True, interactive=False)
                time.sleep(UPDATE_INTERVAL)
            except Error:
                logging.exception("Google Docs exception:")
                time.sleep(RETRY_INTERVAL)
            except Exception:
                logging.exception("Daemon exception:")
                break

        logging.debug("Daemon exiting...")
