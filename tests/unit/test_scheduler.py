#!/usr/bin/env python3
"""Unit tests for the config file parsing module."""
import logging
from unittest.mock import patch

import pytest

from experiment.scheduler.scheduler import EcflowClient, EcflowServer, EcflowTask


def suite_name():
    return "test_suite"


@pytest.fixture()
@patch("experiment.scheduler.scheduler.ecflow")
def ecflow_task(__):
    ecf_name = f"/{suite_name}/family/Task"
    ecf_tryno = "1"
    ecf_pass = "abc123"  # noqa S108
    ecf_rid = None
    ecf_timeout = 20
    return EcflowTask(ecf_name, ecf_tryno, ecf_pass, ecf_rid, ecf_timeout=ecf_timeout)


@pytest.fixture()
@patch("experiment.scheduler.scheduler.ecflow")
def ecflow_server(__):
    ecf_host = "localhost"
    return EcflowServer(ecf_host)


class TestScheduler:
    # pylint: disable=no-self-use

    def test_ecflow_client(self, ecflow_server, ecflow_task):
        EcflowClient(ecflow_server, ecflow_task)

    @patch("experiment.scheduler.scheduler.ecflow")
    def test_start_suite(self, mock, ecflow_server):
        logging.debug("Print mock: %s", mock)
        def_file = f"/tmp/{suite_name()}.def"  # noqa
        ecflow_server.start_suite(suite_name(), def_file)
        logging.debug("Print mock: %s", mock)
