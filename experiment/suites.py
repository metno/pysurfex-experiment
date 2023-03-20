"""Suite for experiment."""
import os


from .scheduler.submission import TaskSettings, TroikaSettings
from .scheduler.suites import EcflowSuite, EcflowSuiteFamily, EcflowSuiteTask,\
    EcflowSuiteTrigger, EcflowSuiteTriggers
from .logs import get_logger_from_config
from .datetime_utils import as_datetime, as_timedelta
from .progress import ProgressFromConfig
from .toolbox import Platform
from .configuration import Configuration


class SurfexSuite():
    """Surfex suite."""

    def __init__(self, suite_name, config, joboutdir, task_settings, dtgs, next_start_dtg, dtgbeg=None, ecf_micro="%"):
        """Initialize a SurfexSuite object.

        Args:
            suite_name (str): Name of the suite
            exp (experiment.Exp): Configuration you want to run
            joboutdir (str): Directory for job and log files
            TaskSettings (TaskSettings): Submission environment for jobs
            dtgs (list): The DTGs you want to run
            next_start_dtg (datetime): Next DTG to run after this DTG
            dtgbeg (datetime, optional): First DTG the experiment run. Defaults to None.

        """
        if dtgbeg is None:
            dtgbeg_str = dtgs[0].strftime("%Y%m%d%H%M")
        else:
            dtgbeg_str = dtgbeg.strftime("%Y%m%d%H%M")

        # config = exp_config.sfx_config
        self.config = config
        logger = get_logger_from_config(self.config)
        settings = Configuration(config)
        platform = Platform(config)
        progress = ProgressFromConfig(config)
        exp_dir = f"{platform.get_system_value('exp_dir')}"
        ecf_include = exp_dir + "/ecf"
        ecf_files = joboutdir
        os.makedirs(ecf_files, exist_ok=True)
        template = f"{platform.get_system_value('pysurfex_experiment')}/experiment/templates/ecflow/default.py"
        ecf_home = joboutdir
        ecf_out = joboutdir
        ecf_jobout = joboutdir + "/%ECF_NAME%.%ECF_TRYNO%"
        os.makedirs(ecf_out, exist_ok=True)
        logger.debug("ECF_HOME: %s", ecf_home)

        # Commands started from the scheduler does not have full environment
        ecf_job_cmd = (
            f"{ecf_micro}TROIKA{ecf_micro} "
            f"-c {ecf_micro}TROIKA_CONFIG{ecf_micro} submit "
            f"-o {ecf_micro}ECF_JOBOUT{ecf_micro} "
            f"{ecf_micro}SCHOST{ecf_micro} "
            f"{ecf_micro}ECF_JOB{ecf_micro}"
        )
        # %ECF_JOB%"
        ecf_status_cmd = (
            f"{ecf_micro}TROIKA{ecf_micro} "
            f"-c {ecf_micro}TROIKA_CONFIG{ecf_micro} monitor "
            f"{ecf_micro}SCHOST{ecf_micro} "
            f"{ecf_micro}ECF_JOB{ecf_micro}"
        )
        ecf_kill_cmd = (
            f"{ecf_micro}TROIKA{ecf_micro} "
            f"-c {ecf_micro}TROIKA_CONFIG{ecf_micro} kill "
            f"{ecf_micro}SCHOST{ecf_micro} "
            f"{ecf_micro}ECF_JOB{ecf_micro}"
        )

        try:
            config_file = config.get_value("metadata.source_file_path")
        except AttributeError:
            config_file = "NO_CONFIG_FOUND"
        loglevel = "INFO"
        variables = {
            "ECF_EXTN": ".py",
            "ECF_FILES": ecf_files,
            "ECF_INCLUDE": ecf_include,
            "ECF_TRIES": 1,
            "ECF_HOME": ecf_home,
            "ECF_KILL_CMD": ecf_kill_cmd,
            "ECF_JOB_CMD": ecf_job_cmd,
            "ECF_STATUS_CMD": ecf_status_cmd,
            "ECF_OUT": ecf_out,
            "ECF_JOBOUT": ecf_jobout,
            "ECF_TIMEOUT": 20,
            "LOGLEVEL": loglevel,
            "WRAPPER": "",
            "VAR_NAME": "",
            "CONFIG": str(config_file),
            "TROIKA": TroikaSettings(config).command,
            "TROIKA_CONFIG": TroikaSettings(config).config,
            "EXP_DIR": exp_dir,
            "EXP": config.get_value("general.case"),
            "DTG": dtgbeg_str,
            "DTGPP": dtgbeg_str,
            "STREAM": "",
            "ENSMBR": "",
            "ARGS": "",
            "FORCE": "",
            "CHECK_EXISTENCE": "",
            "PRINT_NAMELIST": ""
        }
        realization = None
        self.suite_name = suite_name
        logger.debug("variables: %s", variables)
        self.suite = EcflowSuite(self.suite_name, ecf_files, variables=variables, dry_run=False)

        if config.get_value("compile.build"):
            comp = EcflowSuiteFamily("Compilation", self.suite, ecf_files)
            sync = EcflowSuiteTask("SyncSourceCode", comp,
                                   config, task_settings, ecf_files, input_template=template)
            sync_complete = EcflowSuiteTrigger(sync, mode="complete")
            configure = EcflowSuiteTask("ConfigureOfflineBinaries", comp,
                                        config, task_settings, ecf_files, input_template=template,
                                        triggers=EcflowSuiteTriggers([sync_complete]))
            configure_complete = EcflowSuiteTrigger(configure, mode="complete")
            EcflowSuiteTask("MakeOfflineBinaries", comp, config, task_settings, ecf_files,
                            input_template=template,
                            triggers=EcflowSuiteTriggers([configure_complete]))
            comp_complete = EcflowSuiteTrigger(comp, mode="complete")
        else:
            comp_complete = None

        triggers = EcflowSuiteTriggers([comp_complete])
        static = EcflowSuiteFamily("StaticData", self.suite, ecf_files, triggers=triggers)
        EcflowSuiteTask("Pgd", static, config, task_settings, ecf_files, input_template=template)

        static_complete = EcflowSuiteTrigger(static)

        prep_complete = None
        hours_ahead = 24
        cycle_input_dtg_node = {}
        prediction_dtg_node = {}
        post_processing_dtg_node = {}
        prev_dtg = None
        for idtg, dtg in enumerate(dtgs):
            if idtg < (len(dtgs) - 1):
                next_dtg = dtgs[idtg + 1]
            else:
                next_dtg = next_start_dtg
            next_dtg_str = next_dtg.strftime("%Y%m%d%H%M")
            dtg_str = dtg.strftime("%Y%m%d%H%M")
            variables = {
                "DTG": dtg_str,
                "DTG_NEXT": next_dtg_str,
                "DTGBEG": dtgbeg_str
            }
            triggers = EcflowSuiteTriggers([static_complete])

            dtg_node = EcflowSuiteFamily(dtg_str, self.suite, ecf_files, variables=variables,
                                         triggers=triggers)

            ahead_trigger = None
            for dtg_str2 in prediction_dtg_node:
                tname = prediction_dtg_node[dtg_str2]["node"]
                validtime = as_datetime(prediction_dtg_node[dtg_str2]["dtg"])
                if validtime < dtg:
                    if validtime + as_timedelta(f"PT{hours_ahead}H") <= dtg:
                        ahead_trigger = EcflowSuiteTrigger(tname)

            if ahead_trigger is None:
                triggers = EcflowSuiteTriggers([static_complete])
            else:
                triggers = EcflowSuiteTriggers([static_complete,
                                                ahead_trigger])

            prepare_cycle = EcflowSuiteTask("PrepareCycle", dtg_node, config,
                                            task_settings, ecf_files,
                                            triggers=triggers, input_template=template)
            prepare_cycle_complete = EcflowSuiteTrigger(prepare_cycle)

            triggers.add_triggers([EcflowSuiteTrigger(prepare_cycle)])

            cycle_input = EcflowSuiteFamily("CycleInput", dtg_node, ecf_files, triggers=triggers)
            cycle_input_dtg_node.update({dtg_str: cycle_input})

            forcing = EcflowSuiteTask("Forcing", cycle_input, config, task_settings, ecf_files, input_template=template)
            triggers = EcflowSuiteTriggers([EcflowSuiteTrigger(forcing)])
            if config.get_value("forcing.modify_forcing"):
                EcflowSuiteTask("ModifyForcing", cycle_input, config, task_settings, ecf_files,
                                input_template=template, triggers=triggers)

            triggers = EcflowSuiteTriggers([static_complete,
                                            prepare_cycle_complete])
            if prev_dtg is not None:
                prev_dtg_str = prev_dtg.strftime("%Y%m%d%H%M")
                trigger = EcflowSuiteTrigger(prediction_dtg_node[prev_dtg_str]["node"])
                triggers.add_triggers([trigger])

            # Initialization
            initialization = EcflowSuiteFamily("Initialization", dtg_node, ecf_files, triggers=triggers)

            analysis = None
            if dtg == dtgbeg:

                prep = EcflowSuiteTask("Prep", initialization, config, task_settings, ecf_files,
                                       input_template=template)
                prep_complete = EcflowSuiteTrigger(prep)
                # Might need an extra trigger for input

            else:

                schemes = config.get_value("SURFEX.ASSIM.SCHEMES").dict()
                do_soda = False
                for scheme in schemes:
                    if schemes[scheme].upper() != "NONE":
                        do_soda = True

                obs_types = config.get_value("SURFEX.ASSIM.OBS.COBS_M")
                nnco = settings.get_nnco(dtg=dtg)
                for ivar in range(0, len(nnco)):
                    if nnco[ivar] == 1 and obs_types[ivar] == "SWE":
                        do_soda = True

                triggers = EcflowSuiteTriggers(prep_complete)
                if not do_soda:
                    EcflowSuiteTask("CycleFirstGuess", initialization, config, task_settings, ecf_files,
                                    triggers=triggers, input_template=template)
                else:
                    fg_task = EcflowSuiteTask("FirstGuess", initialization,
                                              config, task_settings, ecf_files,
                                              triggers=triggers, input_template=template)

                    perturbations = None
                    if settings.setting_is("SURFEX.ASSIM.SCHEMES.ISBA", "EKF", realization=realization):

                        perturbations = EcflowSuiteFamily("Perturbations", initialization, ecf_files)
                        nncv = config.get_value("SURFEX.ASSIM.ISBA.EKF.NNCV")
                        names = config.get_value("SURFEX.ASSIM.ISBA.EKF.CVAR_M")
                        triggers = None
                        fgint = settings.get_fgint(realization=realization)
                        fg_dtg = progress.dtg - fgint
                        if fg_dtg in cycle_input_dtg_node:
                            triggers = EcflowSuiteTriggers(
                                EcflowSuiteTrigger(cycle_input_dtg_node[fg_dtg]))

                        nivar = 1
                        for ivar, val in enumerate(nncv):
                            logger.debug("ivar %s, nncv[ivar] %s", str(ivar), str(val))
                            if ivar == 0:
                                name = "REF"
                                args = "pert=" + str(ivar) + ";name=" + name + ";ivar=0"
                                logger.debug("args: %s", args)
                                variables = {"ARGS": args}

                                pert = EcflowSuiteFamily(name, perturbations, ecf_files,
                                                         variables=variables)
                                EcflowSuiteTask("PerturbedRun", pert, config, task_settings, ecf_files,
                                                triggers=triggers, input_template=template)
                            if val == 1:
                                name = names[ivar]
                                args = f"pert={str(ivar + 1)};name={name};ivar={str(nivar)}"
                                logger.debug("args: %s", args)
                                variables = {"ARGS": args}
                                pert = EcflowSuiteFamily(name, perturbations, ecf_files,
                                                         variables=variables)
                                EcflowSuiteTask("PerturbedRun", pert, config, task_settings, ecf_files,
                                                triggers=triggers, input_template=template)
                                nivar = nivar + 1

                    prepare_oi_soil_input = None
                    prepare_oi_climate = None
                    if settings.setting_is("SURFEX.ASSIM.SCHEMES.ISBA", "OI"):
                        prepare_oi_soil_input = EcflowSuiteTask("PrepareOiSoilInput",
                                                                initialization,
                                                                config, task_settings, ecf_files,
                                                                input_template=template)
                        prepare_oi_climate = EcflowSuiteTask("PrepareOiClimate",
                                                             initialization,
                                                             config, task_settings, ecf_files,
                                                             input_template=template)

                    prepare_sst = None
                    if settings.setting_is("SURFEX.ASSIM.SCHEMES.SEA", "INPUT"):
                        if settings.setting_is("SURFEX.ASSIM.SEA.CFILE_FORMAT_SST", "ASCII"):
                            prepare_sst = EcflowSuiteTask("PrepareSST", initialization,
                                                          config, task_settings, ecf_files,
                                                          input_template=template)

                    an_variables = {"t2m": False, "rh2m": False, "sd": False}
                    obs_types = config.get_value("SURFEX.ASSIM.OBS.COBS_M")
                    nnco = settings.get_nnco(dtg=dtg)
                    for t_ind, val in enumerate(obs_types):
                        if nnco[t_ind] == 1:
                            if obs_types[t_ind] == "T2M" or obs_types[t_ind] == "T2M_P":
                                an_variables.update({"t2m": True})
                            elif obs_types[t_ind] == "HU2M" or obs_types[t_ind] == "HU2M_P":
                                an_variables.update({"rh2m": True})
                            elif obs_types[t_ind] == "SWE":
                                an_variables.update({"sd": True})

                    analysis = EcflowSuiteFamily("Analysis", initialization, ecf_files)
                    fg4oi = EcflowSuiteTask("FirstGuess4OI", analysis,
                                            config, task_settings, ecf_files, input_template=template)
                    fg4oi_complete = EcflowSuiteTrigger(fg4oi)

                    triggers = []
                    for var, active in an_variables.items():
                        if active:
                            variables = {"VAR_NAME": var}
                            an_var_fam = EcflowSuiteFamily(var, analysis, ecf_files, variables=variables)
                            qc_triggers = None
                            if var == "sd":
                                qc_triggers = EcflowSuiteTriggers(fg4oi_complete)
                            qc_task = EcflowSuiteTask("QualityControl", an_var_fam,
                                                      config, task_settings, ecf_files, triggers=qc_triggers,
                                                      input_template=template)
                            oi_triggers = EcflowSuiteTriggers([
                                EcflowSuiteTrigger(qc_task),
                                EcflowSuiteTrigger(fg4oi)])
                            EcflowSuiteTask("OptimalInterpolation", an_var_fam,
                                            config, task_settings, ecf_files, triggers=oi_triggers,
                                            input_template=template)
                            triggers.append(EcflowSuiteTrigger(an_var_fam))

                    oi2soda_complete = None
                    if len(triggers) > 0:
                        triggers = EcflowSuiteTriggers(triggers)
                        oi2soda = EcflowSuiteTask("Oi2soda", analysis, config, task_settings, ecf_files,
                                                  triggers=triggers, input_template=template)
                        oi2soda_complete = EcflowSuiteTrigger(oi2soda)

                    prepare_lsm = None
                    need_lsm = False
                    if settings.setting_is("SURFEX.ASSIM.SCHEMES.ISBA", "OI"):
                        need_lsm = True
                    if settings.setting_is("SURFEX.ASSIM.SCHEMES.INLAND_WATER", "WATFLX"):
                        if config.get_value("SURFEX.ASSIM.INLAND_WATER.LEXTRAP_WATER"):
                            need_lsm = True
                    if need_lsm:
                        triggers = EcflowSuiteTriggers(fg4oi_complete)
                        prepare_lsm = EcflowSuiteTask("PrepareLSM", initialization,
                                                      config, task_settings, ecf_files,
                                                      triggers=triggers, input_template=template)

                    triggers = [EcflowSuiteTrigger(fg_task), oi2soda_complete]
                    if perturbations is not None:
                        triggers.append(EcflowSuiteTrigger(perturbations))
                    if prepare_oi_soil_input is not None:
                        triggers.append(EcflowSuiteTrigger(prepare_oi_soil_input))
                    if prepare_oi_climate is not None:
                        triggers.append(EcflowSuiteTrigger(prepare_oi_climate))
                    if prepare_sst is not None:
                        triggers.append(EcflowSuiteTrigger(prepare_sst))
                    if prepare_lsm is not None:
                        triggers.append(EcflowSuiteTrigger(prepare_lsm))

                    triggers = EcflowSuiteTriggers(triggers)
                    EcflowSuiteTask("Soda", analysis, config, task_settings, ecf_files, triggers=triggers,
                                    input_template=template)

            triggers = EcflowSuiteTriggers([EcflowSuiteTrigger(cycle_input),
                                            EcflowSuiteTrigger(initialization)])
            prediction = EcflowSuiteFamily("Prediction", dtg_node, ecf_files, triggers=triggers)
            prediction_dtg_node.update({dtg_str: {"node": prediction, "dtg": dtg}})

            forecast = EcflowSuiteTask("Forecast", prediction, config, task_settings, ecf_files,
                                       input_template=template)
            triggers = EcflowSuiteTriggers(EcflowSuiteTrigger(forecast))
            EcflowSuiteTask("LogProgress", prediction,
                            config, task_settings, ecf_files, triggers=triggers, input_template=template)

            triggers = EcflowSuiteTriggers(EcflowSuiteTrigger(prediction))
            pp_fam = EcflowSuiteFamily("PostProcessing", dtg_node, ecf_files, triggers=triggers)
            post_processing_dtg_node.update({dtg_str: pp_fam})

            log_pp_trigger = None
            if analysis is not None:
                qc2obsmon = EcflowSuiteTask("Qc2obsmon", pp_fam, config, task_settings, ecf_files,
                                            input_template=template)
                trigger = EcflowSuiteTrigger(qc2obsmon)
                log_pp_trigger = EcflowSuiteTriggers(trigger)

            EcflowSuiteTask("LogProgressPP", pp_fam, config, task_settings, ecf_files,
                            triggers=log_pp_trigger, input_template=template)

            prev_dtg = dtg

        hours_behind = 24
        for dtg in dtgs:
            dtg_str = dtg.strftime("%Y%m%d%H%M")
            pp_dtg_str = (dtg - as_timedelta(f"PT{hours_behind}H")).strftime("%Y%m%d%H%M")
            if pp_dtg_str in post_processing_dtg_node:
                triggers = EcflowSuiteTriggers(
                    EcflowSuiteTrigger(post_processing_dtg_node[pp_dtg_str]))
                cycle_input_dtg_node[dtg_str].add_part_trigger(triggers)

    def save_as_defs(self, def_file):
        """Save definition file.

        Args:
            def_file (_type_): _description_
        """
        logger = get_logger_from_config(self.config)
        logger.debug("SurfexSuiteDefinition: Saving def file %s", def_file)
        self.suite.save_as_defs(def_file)


def get_defs(config, suite_type):
    """Get the definitions.

    Args:
        config (experiment.ExpConfiguration): Experiment
        suite_type (str): What kind of suite

    Raises:
        Exception: _description_
        NotImplementedError: _description_

    Returns:
        SuiteDefinition: A suite definitition
    """
    logger = get_logger_from_config(config)
    name = config.get_value("general.case")
    settings = Configuration(config)
    suite_name = name.replace("-", "_")
    suite_name = suite_name.replace(".", "_")
    logger.debug("Config name %s", name)
    logger.debug("Get defs for %s", suite_name)

    # system = config.system
    progress = ProgressFromConfig(config)
    platform = Platform(config)
    joboutdir = platform.get_system_value("joboutdir")
    task_settings = TaskSettings(config)
    unique_cycles = settings.get_total_unique_cycle_list()
    dtgstart = progress.dtg
    dtgbeg = progress.dtgbeg
    dtgend = progress.dtgend
    logger.debug("%s: DTGSTART: %s DTGBEG: %s DTGEND: %s", __file__,
                 dtgstart, dtgbeg, dtgend)
    if dtgbeg is None:
        dtgbeg = dtgstart
    dtgs = []
    dtg = dtgstart
    logger.debug("Building list of DTGs")
    cont = True
    while cont:
        for cycle in unique_cycles:
            while dtg <= dtgend:
                dtgs.append(dtg)
                logger.debug("DTG: %s, fcint: %s",
                             dtg, cycle)
                dtg = dtg + cycle
            if dtg >= dtgend:
                cont = False

    logger.debug("Built DTGS: %s", dtgs)
    if suite_type == "surfex":
        return SurfexSuite(suite_name, config, joboutdir, task_settings,
                           dtgs, dtg, dtgbeg=dtgbeg)
    raise NotImplementedError(f"Suite definition for {suite_type} is not implemented!")
