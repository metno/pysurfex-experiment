#!/usr/bin/env python3
"""Handle host detection."""

import os
import re
import socket

import yaml

from deode import GeneralConstants
from deode.logs import logger


class DeodeHost:
    """DeodeHost object."""

    def __init__(self, known_hosts=None):
        """Constructs the DeodeHost object."""
        self.known_hosts = self._load_known_hosts(known_hosts)
        self.available_hosts = list(self.known_hosts)
        self.default_host = self.available_hosts[0]

    def _load_known_hosts(self, known_hosts=None):
        """Loads the known_hosts config.

        Raises:
            RuntimeError: No host identifiers loaded

        Returns:
            known_host (dict): Known hosts config

        """
        known_hosts_file = known_hosts
        if known_hosts_file is None:
            known_hosts_file = os.path.join(
                GeneralConstants.PACKAGE_DIRECTORY, "data", "config_files", "known_hosts.yml"
            )
        with open(known_hosts_file, "rb") as infile:
            known_hosts = yaml.safe_load(infile)

        if known_hosts is None:
            raise RuntimeError(f"No hosts available in {known_hosts_file}")

        return known_hosts

    def _detect_by_hostname(self, hostname_pattern):
        """Detect deode host by hostname regex.

        Args:
            hostname_pattern(list|str) : hostname regex to match

        Returns:
            (boolean): Match or not

        """
        hostname = socket.gethostname()
        logger.info("hostname={}", hostname)
        hh = [hostname_pattern] if isinstance(hostname_pattern, str) else hostname_pattern
        for x in hh:
            if re.match(x, hostname):
                logger.info("Deode-host detected by hostname {}", x)
                return True

        return False

    def _detect_by_env(self, env_variable):
        """Detect deode host by environment variable regex.

        Args:
            env_variable(dict) : Environment variables to search for

        Returns:
            (boolean): Match or not

        """
        for var, value in env_variable.items():
            if var in os.environ:
                vv = [value] if isinstance(value, str) else value
                for x in vv:
                    if re.match(x, os.environ[var]):
                        logger.info(
                            "Deode-host detected by environment variable {}={}", var, x
                        )
                        return True

        return False

    def detect_deode_host(self):
        """Detect deode host by matching various properties.

        Raises:
            RuntimeError: Ambiguous matches

        Returns:
            deode_host (str): mapped hostname

        """
        matches = []
        for deode_host, detect_methods in self.known_hosts.items():
            for method, pattern in detect_methods.items():
                fname = f"_detect_by_{method}"
                if hasattr(self, fname):
                    function = getattr(self, fname)
                    if function(pattern):
                        matches.append(deode_host)
                        break
                else:
                    raise RuntimeError(f"No deode-host detection using {method}")

        if len(matches) == 0:
            matches = list(self.known_hosts)[0:1]
            logger.info(f"No deode-host detected, use {self.default_host}")
        if len(matches) > 1:
            raise RuntimeError(f"Ambiguous matches: {matches}")

        return matches[0]
