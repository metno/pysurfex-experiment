"""Unit testing."""
import os
# import sys
import unittest
from pathlib import Path
import json
# import inspect
# import shutil
import logging
# import toml
import experiment_scheduler
import experiment
import surfex
from unittest.mock import patch
# import experiment_setup
# import experiment_tasks
import ecf
from datetime import datetime

TESTDATA = f"{str((Path(__file__).parent).parent)}/testdata"
ROOT = f"{str((Path(__file__).parent).parent)}"
logging.basicConfig(format='%(asctime)s %(levelname)s %(pathname)s:%(lineno)s %(message)s',
                    level=logging.DEBUG)


class TestFlow(unittest.TestCase):
    """Test config."""

    @classmethod
    def setUpClass(cls):
        ecf_name = "/suite/ecf_name"
        ecf_tryno = 2
        ecf_pass = "12345"
        ecf_rid = 54321
        ecf_timeout = 20
        cls.task = experiment_scheduler.EcflowTask(ecf_name, ecf_tryno, ecf_pass, ecf_rid, ecf_timeout=ecf_timeout)

        wdir = "/tmp/test_config"
        exp_name = "test_config"
        host = "unittest"
        cls.pysurfex_experiment = f"{str((Path(__file__).parent).parent)}"
        pysurfex = f"{str((Path(surfex.__file__).parent).parent)}"
        offline_source = "/tmp/source"
        cls.exp_dependencies = experiment.ExpFromFiles.setup_files(wdir, exp_name, host, pysurfex,
                                                                   cls.pysurfex_experiment,
                                                                   offline_source=offline_source)
        stream = None
        with patch('experiment_scheduler.scheduler.ecflow') as mock_ecflow:
            sfx_exp = experiment.ExpFromFiles(cls.exp_dependencies, stream=stream)

        sfx_exp.settings.update({"PROGRESS": {
            "DTG": "202201010000",
            "DTGBEG": "202201010000",
            "DTGPP": "202201010000"
        }})
        cls.exp_configuration_file = "/tmp/exp_configuration.json"
        sfx_exp.dump_exp_configuration(cls.exp_configuration_file)
        with patch('experiment_scheduler.scheduler.ecflow') as mock_ecflow:
            cls.sfx_exp = experiment.ConfigurationFromJsonFile(cls.exp_configuration_file)

    def test_submit(self):
        pass

    @patch('experiment_scheduler.scheduler.ecflow')
    def test_start_server(self, ecflow):
        """Start the ecflow server."""
        ecf_host = "localhost"
        server = experiment_scheduler.EcflowServer(ecf_host, ecf_port=3141, start_command=None)
        server.start_server()
        ecflow.Client.assert_called_once()

    @patch('experiment_scheduler.scheduler.ecflow')
    def test_server_from_file(self, ecflow):
        """Start the ecflow server from a file definition."""
        server_file = "/tmp/ecflow_server"
        with open(server_file, mode="w", encoding="utf-8") as server_fh:
            json.dump({"ecf_host": "localhost", "ecf_port": 41, "ecf_offset": 3100}, server_fh)
        server = experiment_scheduler.EcflowServer(server_file)
        self.assertEqual(server.ecf_port, 3141, "Port is not 3141!")
        ecflow.Client.assert_called_once()

    @patch('experiment_scheduler.scheduler.ecflow')
    def test_begin_suite(self, ecflow):
        """Begin the suite."""
        ecf_host = "localhost"
        server = experiment_scheduler.EcflowServer(ecf_host, ecf_port=3141, start_command=None)
        server.begin_suite(self.task)

    @patch('experiment_scheduler.scheduler.ecflow')
    def test_force_complete(self, ecflow):
        """Begin the suite."""
        ecf_host = "localhost"
        server = experiment_scheduler.EcflowServer(ecf_host, ecf_port=3141, start_command=None)
        server.force_complete(self.task)

    @patch('experiment_scheduler.scheduler.ecflow')
    def test_force_aborted(self, ecflow):
        """Force task aborted."""
        ecf_host = "localhost"
        server = experiment_scheduler.EcflowServer(ecf_host, ecf_port=3141, start_command=None)
        server.force_aborted(self.task)

    @patch('experiment_scheduler.scheduler.ecflow')
    def test_replace(self, ecflow):
        """Replace the suite."""
        ecf_host = "localhost"
        server = experiment_scheduler.EcflowServer(ecf_host, ecf_port=3141, start_command=None)
        server.replace("suite", "/dev/null")

    def test_ecflow_task(self):
        """Test the ecflow task wrapper."""
        ecf_name = "/suite/ecf_name"
        ecf_tryno = 2
        ecf_pass = "12345"
        ecf_rid = 54321
        ecf_timeout = 20
        task = experiment_scheduler.EcflowTask(ecf_name, ecf_tryno, ecf_pass, ecf_rid, ecf_timeout=ecf_timeout)
        self.assertEqual(ecf_name, task.ecf_name, "ecf_name differ")
        self.assertEqual(ecf_tryno, task.ecf_tryno, "ecf_tryno differ")
        self.assertEqual(ecf_pass, task.ecf_pass, "ecf_pass differ")
        self.assertEqual(ecf_rid, task.ecf_rid, "ecf_rid differ")
        self.assertEqual(ecf_timeout, task.ecf_timeout, "ecf_timeout differ")

    @patch('experiment_scheduler.scheduler.ecflow')
    def test_suite(self, ecflow):
        pass

    @patch('experiment_scheduler.suites.ecflow')
    def test_ecflow_suite_task(self, ecflow):
        """Create a ecflow suite/family/task structure and create job."""
        ecf_files = "/tmp/"
        suite_name = "suite"
        with patch('experiment_scheduler.suites.ecflow.Defs') as mock_defs:
            suite = experiment_scheduler.EcflowSuite(suite_name, ecf_files)
        family_name = "family"
        family = experiment_scheduler.EcflowSuiteFamily(family_name, suite, ecf_files)
        task_name = "task"
        config = self.sfx_exp
        task_settings = experiment_scheduler.TaskSettings(self.sfx_exp.env_submit)
        input_template = f"{ROOT}/ecf/stand_alone.py"
        with patch('experiment_scheduler.submission.TaskSettings.parse_job') as mock_task:
            experiment_scheduler.EcflowSuiteTask(task_name, family, config, task_settings,
                                                 ecf_files, input_template=input_template,
                                                 parse=True, variables=None, ecf_micro="%",
                                                 triggers=None, def_status=None)
        # job_file = f"{ecf_files}/{suite_name}/{family_name}/{task_name}.py"
        # self.assertTrue(os.path.exists(job_file), "Job file is missing")

    '''
    def test_default(self):
        """Test default ecf container."""
        kwargs_main = ecf.default.parse_ecflow_vars()
        ecf.default_main(**kwargs_main)

    @patch('experiment_tasks.tasks.AbstractTask')
    def test_stand_alone(self, task):
        """Test stand alone container."""
        TASK_NAME = "Forecast"
        CONFIG = self.exp_configuration_file
        LOGLEVEL = "DEBUG"
        ecf.stand_alone_main(TASK_NAME, CONFIG, LOGLEVEL)
    '''

    @patch('experiment_scheduler.submission.TaskSettings.parse_job')
    def test_ecflow_sufex_suite(self, mock):
        suite_name = "suite"
        joboutdir = "/tmp"
        exp = self.sfx_exp
        task_settings = experiment_scheduler.TaskSettings(self.sfx_exp.env_submit)
        dtg1 = datetime(2022, 1, 1, 0, 0)
        dtg2 = datetime(2022, 1, 1, 6, 0)
        dtgs = [dtg1, dtg2]
        dtgbeg = dtg1
        next_start_dtg = dtg2
        print(exp.progress.dtg)
        with patch('experiment_scheduler.suites.ecflow') as mock_ecflow:
            experiment.SurfexSuite(suite_name, exp, joboutdir, task_settings, dtgs,
                                   next_start_dtg, dtgbeg=dtgbeg, ecf_micro="%")