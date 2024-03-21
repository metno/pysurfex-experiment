#!/usr/bin/env python3
"""Unit tests for the config file parsing module."""
import os
import subprocess
from pathlib import Path

import numpy as np
import pysurfex
import pytest
from pysurfex.geo import ConfProj
from pysurfex.run import BatchJob

import experiment
from experiment import PACKAGE_NAME
from experiment.config_parser import ParsedConfig
from experiment.datetime_utils import as_datetime
from experiment.experiment import Exp, ExpFromFiles
from experiment.logs import logger
from experiment.system import System
from experiment.tasks.discover_tasks import discover, get_task
from experiment.tasks.tasks import AbstractTask

WORKING_DIR = Path.cwd()

logger.enable(PACKAGE_NAME)


def classes_to_be_tested():
    """Return the names of the task-related classes to be tested."""
    encountered_classes = discover(
        experiment.tasks, AbstractTask, attrname="__type_name__"
    )
    return encountered_classes.keys()


@pytest.fixture(scope="module")
def get_config(tmp_path_factory):
    wdir = f"{tmp_path_factory.getbasetemp().as_posix()}"
    exp_name = "test_config"
    pysurfex_experiment = f"{str(((Path(__file__).parent).parent).parent)}"
    pysurfex_path = f"{str((Path(pysurfex.__file__).parent).parent)}"
    offline_source = f"{wdir}/source"

    exp_dependencies = ExpFromFiles.setup_files(
        wdir,
        exp_name,
        None,
        pysurfex_path,
        pysurfex_experiment,
        offline_source=offline_source,
    )

    scratch = f"{tmp_path_factory.getbasetemp().as_posix()}"
    env_system = {
        "host_system": {
            "compcentre": "LOCAL",
            "hosts": ["my_host_0", "my_host_1"],
            "sfx_exp_data": f"{scratch}/host0/@EXP@",
            "sfx_exp_lib": f"{scratch}/host0/@EXP@/lib",
            "host_name": "",
            "joboutdir": f"{scratch}/host0/job",
            "hm_cs": "gfortran",
            "parch": "",
            "mkdir": "mkdir -p",
            "rsync": 'rsync -avh -e "ssh -i ~/.ssh/id_rsa"',
            "surfex_config": "my_harmonie_config",
            "login_host": "localhost",
            "scheduler_pythonpath": "",
            "host1": {
                "sfx_exp_data": f"{scratch}/host1/@EXP@",
                "sfx_exp_lib": f"{scratch}/host1/@EXP@/lib",
                "host_name": "",
                "joboutdir": f"{scratch}/host1/job",
                "login_host": "localhost",
                "sync_data": True,
            },
        }
    }

    system = System(env_system, exp_name)
    system_file_paths = {
        "soilgrid_data_path": f"{tmp_path_factory.getbasetemp().as_posix()}",
        "ecoclimap_bin_dir": f"{tmp_path_factory.getbasetemp().as_posix()}",
        "ecosg_data_path": f"{tmp_path_factory.getbasetemp().as_posix()}",
        "pgd_data_path": f"{tmp_path_factory.getbasetemp().as_posix()}",
        "scratch": f"{tmp_path_factory.getbasetemp().as_posix()}",
        "static_data": f"{tmp_path_factory.getbasetemp().as_posix()}",
        "climdata": f"{tmp_path_factory.getbasetemp().as_posix()}",
        "prep_input_file": f"{tmp_path_factory.getbasetemp().as_posix()}"
        + "/demo/ECMWF/archive/2023/02/18/18/fc20230218_18+006",
        "gmted2010_data_path": f"{tmp_path_factory.getbasetemp().as_posix()}/GMTED2010",
    }

    env_submit = {
        "submit_types": ["background", "scalar"],
        "default_submit_type": "scalar",
        "background": {
            "HOST": "0",
            "OMP_NUM_THREADS": 'import os\nos.environ.update({"OMP_NUM_THREADS": "1"})',
            "tasks": ["InitRun", "LogProgress", "LogProgressPP"],
        },
        "scalar": {
            "HOST": "1",
            "Not_existing_task": {"DR_HOOK": 'print("Hello world")'},
        },
    }
    progress = {
        "basetime": "2023-01-01T03:00:00Z",
        "start": "2023-01-01T00:00:00Z",
        "end": "2023-01-01T06:00:00Z",
        "basetime_pp": "2023-01-01T03:00:00Z",
    }

    # Configuration
    config_files_dict = ExpFromFiles.get_config_files(
        exp_dependencies["config"]["config_files"], exp_dependencies["config"]["blocks"]
    )
    merged_config = ExpFromFiles.merge_dict_from_config_dicts(config_files_dict)

    # Update domain
    domain_file = f"{pysurfex_experiment}/data/config/domains/Harmonie_domains.json"
    domain = ExpFromFiles.update_domain_from_json_file(
        domain_file, merged_config["domain"]
    )
    merged_config.update({"domain": domain})

    # Create Exp/Configuration object
    stream = None
    env_server = {"ECF_HOST": "localhost"}
    sfx_exp = Exp(
        exp_dependencies,
        merged_config,
        system,
        system_file_paths,
        env_server,
        env_submit,
        progress,
        stream=stream,
        json_schema={},
    )

    config_file = f"{tmp_path_factory.getbasetemp().as_posix()}/config.json"
    sfx_exp.dump_json(config_file)
    config = ParsedConfig.from_file(config_file)
    # Template variables
    update = {
        "task": {
            "args": {
                "check_existence": False,
                "pert": 1,
                "ivar": 1,
                "print_namelist": True,
            }
        }
    }
    config = config.copy(update=update)
    return config


@pytest.fixture(params=classes_to_be_tested())
def task_name_and_configs(request, get_config):
    """Return a ParsedConfig with a task-specific section according to `params`."""
    task_name = request.param
    task_config = get_config
    return task_name, task_config


@pytest.fixture(scope="module")
def _mockers_for_task_run_tests(session_mocker, tmp_path_factory):
    """Define mockers used in the tests for the tasks' `run` methods."""
    # Keep reference to the original methods that will be replaced with wrappers
    original_batchjob_init_method = BatchJob.__init__
    original_batchjob_run_method = BatchJob.run

    # Define the wrappers that will replace some key methods
    def new_batchjob_init_method(self, *args, **kwargs):
        """Remove eventual `wrapper` settings, which are not used for tests."""
        original_batchjob_init_method(self, *args, **kwargs)
        self.wrapper = ""

    def new_write_obsmon_sqlite_file(*args, **kwargs):
        """Run the original method with a dummy cmd if the original cmd fails."""
        pass

    def new_converter(*args, **kwargs):
        pass

    def new_oi2soda(*args, **kwargs):
        pass

    def new_horizontal_oi(*args, **kwargs):
        pass

    def new_read_first_guess_netcdf_file(*args, **kwargs):
        geo_dict = {
            "nam_pgd_grid": {"cgrid": "CONF PROJ"},
            "nam_conf_proj": {"xlat0": 59.5, "xlon0": 9},
            "nam_conf_proj_grid": {
                "ilone": 0,
                "ilate": 0,
                "xlatcen": 60,
                "xloncen": 10,
                "nimax": 50,
                "njmax": 60,
                "xdx": 2500.0,
                "xdy": 2500.0,
            },
        }
        geo = ConfProj(geo_dict)
        validtime = as_datetime("2023-01-01 T03:00:00Z")
        dummy = np.empty([50, 60])
        return geo, validtime, dummy, dummy, dummy

    def new_read_cryoclim_nc(infiles, cryo_varname=""):
        lons = np.ma.array([[10, 10, 10], [10.1, 10.1, 10.1]])
        lats = np.ma.array([[60, 60, 60], [60.1, 60.1, 60.1]])
        vals = np.ma.array([[[0, 1, 2], [3, 4, 5]]])
        return lons, lats, vals

    def new_write_analysis_netcdf_file(*args, **kwargs):
        pass

    def new_dataset_from_file(*args, **kwargs):
        return {}

    def new_converted_input(*args, **kwargs):
        return np.empty([3000])

    def new_surfex_binary(*args, **kwargs):
        pass

    def new_batchjob_run_method(self, cmd):
        """Run the original method with a dummy cmd if the original cmd fails."""
        try:
            original_batchjob_run_method(self, cmd=cmd)
        except subprocess.CalledProcessError:
            original_batchjob_run_method(
                self, cmd="echo 'Running a dummy command' >| output"
            )
            os.system("touch PGD.nc")  # noqa S605
            os.system("touch PREP.nc")  # noqa S605
            os.system("touch SURFOUT.nc")  # noqa S605

    # Do the actual mocking
    session_mocker.patch("pysurfex.run.BatchJob.__init__", new=new_batchjob_init_method)
    session_mocker.patch(
        "pysurfex.obsmon.write_obsmon_sqlite_file", new=new_write_obsmon_sqlite_file
    )
    session_mocker.patch("pysurfex.read.Converter", new=new_converter)
    session_mocker.patch("pysurfex.netcdf.oi2soda", new=new_oi2soda)
    session_mocker.patch(
        "pysurfex.read.ConvertedInput.read_time_step", new=new_converted_input
    )
    session_mocker.patch(
        "experiment.tasks.tasks.read_first_guess_netcdf_file",
        new=new_read_first_guess_netcdf_file,
    )
    session_mocker.patch(
        "experiment.tasks.tasks.dataset_from_file", new=new_dataset_from_file
    )
    session_mocker.patch("experiment.tasks.tasks.horizontal_oi", new=new_horizontal_oi)
    session_mocker.patch(
        "experiment.tasks.tasks.write_analysis_netcdf_file",
        new=new_write_analysis_netcdf_file,
    )
    session_mocker.patch(
        "pysurfex.pseudoobs.read_cryoclim_nc", new=new_read_cryoclim_nc
    )
    session_mocker.patch(
        "experiment.tasks.tasks.write_obsmon_sqlite_file",
        new=new_write_obsmon_sqlite_file,
    )
    session_mocker.patch("experiment.tasks.tasks.oi2soda", new=new_oi2soda)

    session_mocker.patch(
        "experiment.tasks.surfex_binary_task.PerturbedOffline", new=new_surfex_binary
    )
    session_mocker.patch(
        "experiment.tasks.surfex_binary_task.SURFEXBinary", new=new_surfex_binary
    )
    session_mocker.patch("pysurfex.run.BatchJob.run", new=new_batchjob_run_method)

    # Create files needed by gmtedsoil tasks
    tif_files_dir = tmp_path_factory.getbasetemp() / "GMTED2010"
    tif_files_dir.mkdir()
    for fname in ["50N000E_20101117_gmted_mea075", "30N000E_20101117_gmted_mea075"]:
        fpath = tif_files_dir / f"{fname}.tif"
        fpath.touch()

    # Create CMake config file
    cmake_config_dir = (
        f"{tmp_path_factory.getbasetemp().as_posix()}/source/util/cmake/config/"
    )
    print(cmake_config_dir)
    os.makedirs(cmake_config_dir, exist_ok=True)
    cmake_config = (
        tmp_path_factory.getbasetemp()
        / "source/util/cmake/config/config.my_harmonie_config.json"
    )
    cmake_config.touch()

    bin_files = ["PGD-offline", "PREP-offline", "SODA-offline", "OFFLINE-offline"]
    bin_dir = f"{tmp_path_factory.getbasetemp().as_posix()}/host0/test_config/lib/offline/bin/"
    os.makedirs(bin_dir, exist_ok=True)
    for bfile in bin_files:
        bin_file = (
            tmp_path_factory.getbasetemp()
            / f"host0/test_config/lib/offline/bin/{bfile}"
        )
        bin_file.touch()

    # Mock things that we don't want to test here (e.g., external binaries)
    session_mocker.patch("experiment.tasks.gmtedsoil._import_gdal")


class TestTasks:
    # pylint: disable=no-self-use
    """Test all tasks."""

    def test_task_can_be_instantiated(self, task_name_and_configs):
        class_name, task_config = task_name_and_configs
        assert isinstance(get_task(class_name, task_config), AbstractTask)

    @pytest.mark.usefixtures("_mockers_for_task_run_tests")
    def test_task_can_be_run(self, task_name_and_configs):
        class_name, task_config = task_name_and_configs
        my_task_class = get_task(class_name, task_config)
        my_task_class.var_name = "t2m"
        my_task_class.fc_start_sfx = f"{my_task_class.fc_start_sfx}_{class_name}"
        my_task_class.run()
