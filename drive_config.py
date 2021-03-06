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

import os, sys, logging, shutil, csv, ConfigParser, stat

from log import Formatter


_LOG_LEVELS = { "NONE":     None, 
                "DEBUG":    logging.DEBUG, 
                "INFO":     logging.INFO, 
                "WARNING":  logging.WARNING, 
                "ERROR":    logging.ERROR, 
                "CRITICAL": logging.CRITICAL, 
                "FATAL":    logging.FATAL
}


class DriveConfig(object):
    "Google Drive configuration class."
     
    # OAuth 2.0 configuration data.
    APP_NAME = "GDrive-Sync-v1"
    CLIENT_ID = '601991085534.apps.googleusercontent.com'
    CLIENT_SECRET = 'HEGv8uk4mXZ41nLmOlGMbGGu'
    REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
    SCOPES = ["https://www.googleapis.com/auth/userinfo.email", 
              "https://www.googleapis.com/auth/userinfo.profile", 
              "https://docs.google.com/feeds/", 
              "https://docs.googleusercontent.com/", 
              "https://spreadsheets.google.com/feeds/"]
    USER_AGENT = 'gdrive-sync/1.0'
    
    CONFIG_DIR = '.config/%s' % CLIENT_ID   # Configuration directory.
    TOKEN_FILE = 'token.txt'                # Token blob file name. 
    METADATA_FILE = 'metadata.dat'          # Metadata file name.
    CONFIG_FILE = 'gdrive.cfg'              # Configuration file name.
    PID_FILE = 'drived.pid'                 # PID file name.
    LOG_FILE = 'drived.log'                 # Log file name.
    MAX_RESULTS = 500                       # Maximum results to return per request.
    
    # URI to get the root feed. 
    ROOT_FEED_URI = "/feeds/default/private/full/folder%3Aroot/contents"

    # The href of the root folder. If a resource parent is this, then it lives in the root folder.
    ROOT_FOLDER_HREF = "https://docs.google.com/feeds/default/private/full/folder%3Aroot"
    
    # Default configuration values, for user-configurable options. 
    CONFIG_DEFAULTS = { 
        "localstore": { 
            "path": ""                  # The path to the root of the local copy of the folder tree.
        }, 
        "general": { 
            "excludes": "",             # A comma-delimited list of strings specifying paths to be ignored.
        },
        "logging": {
            "level": "NONE"             # Sets the log-level (NONE, DEBUG, INFO, WARN, ERROR).
        }
    }

    def __init__(self, verbose=False, debug=False, logger=None):
        "Class constructor."
        
        self._verbose = verbose
        self._debug = debug
        self._config = {}       # Configuration dict.
        self._logger = logger   # Supplied logger overrides.
        
        if logger == None:
            formatter = Formatter(debug)
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            self._logger = logging.getLogger()
            if self._logger.handlers:
                for handler in self._logger.handlers:
                    self._logger.removeHandler(handler)
            self._logger.addHandler(handler)
            if debug:
                self._logger.setLevel(logging.DEBUG)
            elif verbose:
                self._logger.setLevel(logging.INFO)
            else:
                self._logger.setLevel(logging.WARNING)

        # Load configuration (if any), or initialise to default.
        self.loadConfig()
        
    def getHomeDir(self):
        "Get the users home directory."
        home = os.getenv("XDG_CONFIG_HOME") 
        if home == None:
            home = os.getenv("HOME")
            if home == None:
                sys.exit("Error: user home directory is not defined!")
        return home

    def getConfigDir(self):
        "Find (create if necessary) the configuration directory."
        cfgdir = os.path.join(self.getHomeDir(), self.CONFIG_DIR)
        if os.path.exists(cfgdir):
            if not os.path.isdir(cfgdir):
                sys.exit("Error: \"%s\" exists but is not a directory!" % cfgdir)
        else:
            os.makedirs(cfgdir, 0775)
        return cfgdir

    def getConfigFile(self, name):
        "Get the path to a file in the configuration directory."
        path = os.path.join(self.getConfigDir(), name)
        if os.path.exists(path):
            if not os.path.isfile(path):
                sys.exit("Error: path \"%s\" exists but is not a file!" % path)
        return path

    def getTokenFile(self):
        return self.getConfigFile(self.TOKEN_FILE)

    def getMetadataFile(self):
        return self.getConfigFile(self.METADATA_FILE)

    def getPidFile(self):
        return self.getConfigFile(self.PID_FILE)

    def getLogFile(self):
        return self.getConfigFile(self.LOG_FILE)

    def defaultConfig(self):
        logging.debug("Using default configuration...")
        self._config = self.CONFIG_DEFAULTS.copy()
        
    def loadConfig(self):
        """Load a dictionary of configuration data, from the configuration, 
           file if it exists, or initialise with default values otherwise."""
        self._config = {}
        config = ConfigParser.RawConfigParser()
        cfgfile = self.getConfigFile(self.CONFIG_FILE)
        if os.path.exists(cfgfile):
            logging.debug("Reading configuration...")
            config.read(cfgfile)
            sections = config.sections()
            sections.sort()
            for section in sections:
                self._config[section] = {}
                options = config.options(section)
                for option in options:
                    if option == "excludes":
                        exclist = []
                        parser = csv.reader(config.get(section, option), skipinitialspace=True)
                        for fields in parser:
                            for index, field in enumerate(fields):
                                if field == '':
                                    continue
                                exclist.append(field)
                        self._config[section][option] = exclist
                    else:
                        self._config[section][option] = config.get(section, option)
                    logging.debug("Configuration: section=%s option=%s value=%s" % (section, option, self._config[section][option]))
        else:
            self.defaultConfig()
            self.saveConfig()

    def saveConfig(self):
        "Save the current configuration data to the configuration file." 
        config = ConfigParser.RawConfigParser()
        cfgfile = self.getConfigFile(self.CONFIG_FILE)
        if self.checkLocalFile(cfgfile):
            for section in self._config:
                config.add_section(section)
                for option in self._config[section]:
                    if option == "excludes":
                        if self._config[section][option]:
                            excstr = ', '.join(self._config[section][option])
                            config.set(section, option, excstr)
                        else:
                            config.set(section, option, "")
                    else:
                        config.set(section, option, self._config[section][option])
            logging.debug("Writing configuration...")
            f = open(cfgfile, 'w')
            config.write(f)
            f.close()
        else:
            logging.error("Could not write configuration!")

    def getLocalRoot(self):
        "Get the path to the root of the local storage tree."
        return self._config["localstore"]["path"]

    def setLocalRoot(self, path):
        "Set the path to the root of the local storage tree."
        logging.error("Setting local root is not yet implemented!")
        #self._config["localstore"]["path"] = path
        # TODO check for existing tree at new path.
        # TODO move existing local tree to new path.
        self.saveConfig()

    def checkLocalRoot(self):
        "Check if the local storage folder exists, if not create it."
        path = self.getLocalRoot()
        if path:
            if not os.path.exists(path):
                logging.debug("Creating local storage tree at %s" % path)
                os.mkdir(path)
                return path
            if not os.path.isdir(path):
                # TODO: handle this?
                logging.error("Local path \"%s\" exists, but is not a folder!" % path)
                return None
        else:
            logging.warn("Local storage path is not specified!")
        return path

    def getLocalPath(self, path):
        "Return the local path corresponding to the specified remote path."
        root = self.getLocalRoot()
        if path == '/':
            return root
        if path.startswith(root):
            return path
        if os.path.isabs(path):
            # Strip the leading slash, otherwise os.path.join throws away any preceding paths in the list.
            path = path[1:]
        return os.path.join(root, path)

    def getRemotePath(self, path):
        "Return the remote path corresponding to the specified local path."
        root = self.getLocalRoot()
        if path.startswith(root):
            return path[len(root):]
        return path

    def getExcludes(self):
        "Get the list of folders/files to be excluded."
        return self._config["general"]["excludes"]

    def setExcludes(self, exclist):
        "Set the list of folders/files to be excluded."
        logging.error("Setting local root is not yet implemented!")
        #self._config["general"]["excludes"] = exclist
        # TODO check for existing tree at new path.
        # TODO move existing local tree to new path.
        self.saveConfig()

    def getLogLevel(self):
        "Get the logging level."
        try:
            level = self._config["logging"]["level"].upper()
        except KeyError:
            level = self.CONFIG_DEFAULTS["logging"]["level"].upper()
        try:
            return _LOG_LEVELS[level]
        except KeyError:
            return None

    def checkLocalFile(self, path, overwrite=False):
        "Return True if it is safe to write to the specified file."
        if not os.path.exists(path):
            return True
        if not os.path.isfile(path):
            # TODO: handle this?
            logging.error("Local path \"%s\" exists, but is not a file!" % path)
            return False
        if not overwrite:
            answer = raw_input("Local file \"%s\" already exists, overwrite? (y/N):" % path)
            if answer.upper() != 'Y':
                return False
        logging.debug("Removing \"%s\"..." % path)
        os.remove(path)
        return True

    def checkLocalFolder(self, path, overwrite=False):
        "Return True if it is safe to write to the specified folder."
        if not os.path.exists(path):
            os.mkdir(path)
            return True
        if not os.path.isdir(path):
            # TODO: handle this?
            logging.error("Local path \"%s\" exists, but is not a folder!" % path)
            return False
        if not overwrite:
            answer = raw_input("Local folder \"%s\" already exists, overwrite? (y/N):" % path)
            if answer.upper() != 'Y':
                return False
            logging.debug("Removing \"%s\"..." % path)
            shutil.rmtree(path)
            os.mkdir(path)
            os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return True

    def getLogger(self):
        return self._logger

