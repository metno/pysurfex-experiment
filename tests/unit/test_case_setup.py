"""Test case setup."""
import os
import tomlkit
import pytest
import difflib
from pathlib import Path
from toml_formatter.formatter_options import FormatterOptions
from toml_formatter.formatter import FormattedToml

from deode import GeneralConstants
from deode.config_parser import ParsedConfig, ConfigParserDefaults
from experiment.experiment import case_setup


@pytest.fixture(scope="module")
def tmp_directory(tmp_path_factory):
    """Return a temp directory valid for this module."""
    return tmp_path_factory.getbasetemp().as_posix()

@pytest.fixture()
def test_domain():
    """Return a test domain."""
    domain = {
        "gridtype": "linear",
        "name": "TEST_DOMAIN",
        "nimax": 50,
        "njmax": 60,
        "tstep": 75,
        "xdx": 2500.0,
        "xdy": 2500.0,
        "xlat0": 60.0,
        "xlatcen": 60.0,
        "xlon0": 10.0,
        "xloncen": 10.0,
    }
    return domain


@pytest.fixture()
def default_config_dir():
    rootdir = f"{os.path.dirname(__file__)}/../.."
    return f"{rootdir}/data/config/"


@pytest.fixture(scope="module")
def default_config():
    default_config = os.path.join(
        GeneralConstants.PACKAGE_DIRECTORY, "data", "config_files", "config.toml"
    )
    config = ParsedConfig.from_file(default_config, json_schema=ConfigParserDefaults.MAIN_CONFIG_JSON_SCHEMA)
    return config


def test_save_config(tmp_directory, default_config):
    saved_config = f"{tmp_directory}/saved_config.toml"
    config = default_config
    config.save_as(saved_config)
    config = ParsedConfig.from_file(saved_config, json_schema=ConfigParserDefaults.MAIN_CONFIG_JSON_SCHEMA)


@pytest.fixture()
def _module_mockers_atos_bologna(module_mocker):
    def new_socket_gethostname():
        return "ac6-102.bullx"
    module_mocker.patch("socket.gethostname", new=new_socket_gethostname)



@pytest.mark.usefixtures("_module_mockers_atos_bologna")
def test_set_domain_from_file(tmp_directory, test_domain, default_config, default_config_dir):
    config_dir = f"{tmp_directory}/data/config/"
    #output_file = f"{tmp_directory}/test_set_domain.toml"
    output_file = f"{default_config_dir}/test_set_domain_from_file.toml"
    domains_dir = f"{config_dir}/include/domains"
    os.makedirs(domains_dir, exist_ok=True)
    domain_file = f"{domains_dir}/TEST_DOMAIN.toml"
    with open(domain_file, mode="w", encoding="utf8") as fh:
        tomlkit.dump({"domain": test_domain}, fh)

    case_setup(default_config, output_file, [domain_file], config_dir=default_config_dir)
    config = ParsedConfig.from_file(output_file, json_schema=ConfigParserDefaults.MAIN_CONFIG_JSON_SCHEMA)
    assert config["domain.name"] == "TEST_DOMAIN"
    assert config["domain.name"] == test_domain["name"]
    os.remove(output_file)


@pytest.mark.usefixtures("_module_mockers_atos_bologna")
def test_set_domain_from_name(default_config, default_config_dir):
    output_file = f"{default_config_dir}/test_set_domain_from_name.toml"
    domain = "DEOL"

    case_setup(default_config, output_file, [], domain=domain, config_dir=default_config_dir)
    config = ParsedConfig.from_file(output_file, json_schema=ConfigParserDefaults.MAIN_CONFIG_JSON_SCHEMA)
    assert config["domain.name"] == "DEOL"
    os.remove(output_file)

@pytest.mark.usefixtures("_module_mockers_atos_bologna")
def test_set_case_name(default_config, default_config_dir):
    output_file = f"{default_config_dir}/test_set_case_name.toml"
    case = "a_unique_name"

    case_setup(default_config, output_file, [], case=case, config_dir=default_config_dir)
    config = ParsedConfig.from_file(output_file, json_schema=ConfigParserDefaults.MAIN_CONFIG_JSON_SCHEMA)
    assert config["general.case"] == case
    os.remove(output_file)

def test_write_read_config(default_config, default_config_dir):
    output_file = f"{default_config_dir}/test_write_read_config.toml"
    default_config.save_as(output_file)
    formatter_config = FormatterOptions.from_toml_file("pyproject.toml")
    formatted_toml = FormattedToml.from_file(path=output_file, formatter_options=formatter_config)
    actual_toml = Path(output_file).read_text()

    file_needs_formatting = False
    for __ in difflib.unified_diff(
        actual_toml.split("\n"),
        str(formatted_toml).split("\n"),
        fromfile="Original",
        tofile="Formatted",
        lineterm="",
    ):
        file_needs_formatting = True
    assert not file_needs_formatting
    ParsedConfig.from_file(output_file, json_schema=ConfigParserDefaults.MAIN_CONFIG_JSON_SCHEMA)
