import inspect
import io
import sys
from pylint import lint

import pysenpai.callbacks.defaults as defaults
from pysenpai.output import json_output
from pysenpai.messages import load_messages, Codes
from pysenpai.output import output
from pysenpai.utils.internal import StringOutput, get_exception_line

# NOTE: extra_options, custom_msgs are read only
# therefore setting defaults to empty lists / dictionaries is safe here. 
def pylint_test(st_module,
                lang="en",
                extra_options=[],
                grader=defaults.default_pylint_grader,
                info_only=True,
                custom_msgs={}):
    
    """
    pylint_test(st_module[, lang="en"][, kwarg1][, ...])
    
    Performs a PyLint check on the submitted code module. Mostly just runs PyLint
    inside Python and parses its feedback into messages. Unfortunately PyLint does
    not seem to support gettext so its feedback is always in English. This function
    can be given *extra_options* to be passed to PyLint. Beyond that it uses
    PyLint's configuration discovery. The test can be set to *info_only* in which
    case it never rejects the submission unless there's an error reported by the
    linter. A *validator* can also be provided.
    
    See https://pylint.readthedocs.io/en/latest/user_guide/run.html for information
    regarding configuration and options.
    """
    
    passed = True
    msgs = load_messages(lang, "lint")
    msgs.update(custom_msgs)
    
    json_output.new_test(msgs.get_msg("LintTest", lang)["content"])
    json_output.new_run()
    
    options_list = extra_options + ["--output-format=json", st_module.__file__]
    
    save_o = sys.stdout
    save_e = sys.stderr
    
    o = StringOutput()
    e = StringOutput()
    
    sys.stdout = o
    sys.stderr = e
    
    try:
        result = lint.Run(options_list, do_exit=False)
    except:
        etype, evalue, etrace = sys.exc_info()
        sys.stdout = save_o
        sys.stderr = save_e
        ename = evalue.__class__.__name__
        emsg = str(evalue)
        output(msgs.get_msg(ename, lang, default="GenericErrorMsg"), Codes.ERROR, emsg=emsg, ename=ename)
        return 

    sys.stdout = save_o
    sys.stderr = save_e
            
    try:
        score = grader(result.linter.stats)
    except AssertionError as e:
        score = 0
        if info_only:
            output(msgs.get_msg(e, lang, "LintFailMessage"), Codes.INFO, stats=result.linter.stats)
        else:
            output(msgs.get_msg(e, lang, "LintFailMessage"), Codes.INCORRECT, stats=result.linter.stats)
            passed = False
    else:
        output(msgs.get_msg("LintSuccess", lang), Codes.CORRECT, stats=result.linter.stats)
        
    output(msgs.get_msg("LintMessagesBegin", lang), Codes.INFO)
    
    for msg in result.linter.reporter.messages:
        if msg.category == "convention":
            output(msgs.get_msg("LintConvention", lang), Codes.LINT_C, lintmsg=msg)
        elif msg.category == "refactor":
            output(msgs.get_msg("LintRefactor", lang), Codes.LINT_R, lintmsg=msg)
        elif msg.category == "warning":
            output(msgs.get_msg("LintWarning", lang), Codes.LINT_W, lintmsg=msg)
        elif msg.category == "error":
            output(msgs.get_msg("LintError", lang), Codes.LINT_E, lintmsg=msg)
        elif msg.category == "fatal":
            output(msgs.get_msg("LintFatal", lang), Codes.ERROR, lintmsg=msg)

    return score