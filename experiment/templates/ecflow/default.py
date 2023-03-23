"""Default ecflow container."""
# @ENV_SUB1@

from experiment.config_parser import ParsedConfig
from experiment.datetime_utils import ecflow2datetime_string
from experiment.logs import get_logger_from_config
from experiment.scheduler.scheduler import (
    EcflowClient,
    EcflowServerFromConfig,
    EcflowTask,
)
from experiment.tasks.discover_tasks import get_task

# @ENV_SUB2@


def parse_ecflow_vars():
    """Parse the ecflow variables."""
    return {
        "CONFIG": "%CONFIG%",
        "WRAPPER": "%WRAPPER%",
        "ENSMBR": "%ENSMBR%",
        "DTG": "%DTG%",
        "DTGPP": "%DTGPP%",
        "STREAM": "%STREAM%",
        "TASK_NAME": "%TASK%",
        "VAR_NAME": "%VAR_NAME%",
        "LOGLEVEL": "%LOGLEVEL%",
        "ARGS": "%ARGS%",
        "ECF_NAME": "%ECF_NAME%",
        "ECF_PASS": "%ECF_PASS%",
        "ECF_TRYNO": "%ECF_TRYNO%",
        "ECF_RID": "%ECF_RID%",
    }


"""
%nopp"
"""


def default_main(**kwargs):
    """Ecflow container default method."""
    config = ParsedConfig.from_file(kwargs.get("CONFIG"))
    update = {"general": {"loglevel": kwargs.get("LOGLEVEL")}}
    config = config.copy(update=update)
    logger = get_logger_from_config(config)

    ecf_name = kwargs.get("ECF_NAME")
    ecf_pass = kwargs.get("ECF_PASS")
    ecf_tryno = kwargs.get("ECF_TRYNO")
    ecf_rid = kwargs.get("ECF_RID")
    task = EcflowTask(ecf_name, ecf_tryno, ecf_pass, ecf_rid)
    scheduler = EcflowServerFromConfig(config)

    # This will also handle call to sys.exit(), i.e. Client.__exit__ will still be called.
    with EcflowClient(scheduler, task):
        task_name = kwargs.get("TASK_NAME")
        logger.info("Running task %s", task_name)
        args = kwargs.get("ARGS")
        args_dict = {}
        if args != "":
            logger.debug("args=%s", args)
            for arg in args.split(";"):
                parts = arg.split("=")
                logger.debug("arg=%s parts=%s len(parts)=%s", arg, parts, len(parts))
                if len(parts) == 2:
                    args_dict.update({parts[0]: parts[1]})

        update = {
            "general": {
                "stream": kwargs.get("STREAM"),
                "realization": kwargs.get("ENSMBR"),
                "times": {
                    "basetime": ecflow2datetime_string(kwargs.get("DTG")),
                    "validtime": ecflow2datetime_string(kwargs.get("DTG")),
                    "basetime_pp": ecflow2datetime_string(kwargs.get("DTGPP")),
                },
            },
            "task": {
                "wrapper": kwargs.get("WRAPPER"),
                "var_name": kwargs.get("VAR_NAME"),
                "args": args_dict,
            },
        }
        config = config.copy(update=update)
        get_task(task.ecf_task, config).run()
        logger.info("Finished task %s", task_name)


if __name__ == "__main__":
    # Get ecflow variables
    kwargs_main = parse_ecflow_vars()

    default_main(**kwargs_main)

"""    # noqa
%end"  # noqa
"""  # noqa
