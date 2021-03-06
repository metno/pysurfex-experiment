#!/usr/bin/env python3
import scheduler
import experiment
import os
import sys

lib = "%LIB%"
exp = "%EXP%"
stream = "%STREAM%"
if stream == "":
    stream = None

libs = ["surfex", "scheduler", "experiment"]
for ll in libs:
    if os.path.exists(lib + "/" + ll):
        sys.path.insert(0, lib + "/" + ll)

# InitRun always runs from HOST0
exp = experiment.ExpFromFiles(exp, lib)
server = exp.server

ecf_name = "%ECF_NAME%"
ecf_pass = "%ECF_PASS%"
ecf_tryno = "%ECF_TRYNO%"
ecf_rid = "%ECF_RID%"
submission_id = "%SUBMISSION_ID%"
task = scheduler.EcflowTask(ecf_name, ecf_tryno, ecf_pass, ecf_rid, submission_id)

# This will also handle call to sys.exit(), i.e. Client.__exit__ will still be called.
with scheduler.EcflowClient(server, task) as ci:
    experiment.init_run(exp, stream=stream)
