import inspect
import io
import sys

import pysenpai.callbacks.defaults as defaults
from pysenpai.output import json_output
from pysenpai.messages import load_messages, Codes
from pysenpai.output import output
from pysenpai.utils.internal import StringOutput, get_exception_line

# NOTE: custom_msgs is read only
# therefore setting defaults to empty dictionary is safe here. 
def static_test(st_module, func_names, lang, validators,
                info_only=False,
                custom_msgs={},
                grader=defaults.static_pass_fail_grader):
    """
    static_test(st_module, func_names, lang, validators[, info_only=False[, custom_msgs={}]])
    
    This function performs static tests - i.e. tests that examine the source code
    of the student's program instead of executing it. If *func_names* is a 
    dictionary of languages and corresponding function names, the soure code of 
    that function is subjected to testing. If it is set to None, the module's 
    source code is examined instead. 
    
    The test runs a set of *validators* which should be functions that receive 
    the source code, docstring and comments as seperate arguments. It should use
    asserts. Like in other tests, assert messages are fetched from the message
    dictionary (which can be updated by providing *custom_msgs*). 
    
    If the optional *info_only* flag is set to True, the output in case of issues
    found in the source code is classified as INFO instead of ERROR. This allows 
    you to give the student feedback about dubious solutions without necessarily 
    causing their code to fail the evaluation. 
    """
    
    msgs = load_messages(lang, "static")
    msgs.update(custom_msgs)
    
    #output(msgs.get_msg("StaticTest", lang).format(fname=func_names.get(lang, "")), INFO)
    json_output.new_test(
        msgs.get_msg("StaticTest", lang)["content"].format(fname=func_names.get(lang, ""))
    )
    json_output.new_run()
    
    try:
        if func_names:
            st_func = getattr(st_module, func_names[lang])
            source, doc, comments = inspect.getsource(st_func), inspect.getdoc(st_func), inspect.getcomments(st_func)
        else:
            source, doc, comments = inspect.getsource(st_module), inspect.getdoc(st_module), inspect.getcomments(st_module)
    except:
        etype, evalue, etrace = sys.exc_info()
        ename = evalue.__class__.__name__
        emsg = str(evalue)
        output(msgs.get_msg(ename, lang, default="GenericErrorMsg"), Codes.ERROR,
            fname=func_names.get(lang, ""),
            emsg=emsg,
            ename=ename
        )
        return 
        
    failed = 0
    for validator in validators:
        try: 
            validator(source, doc, comments)
        except AssertionError as e:
            if info_only:
                output(msgs.get_msg(e, lang, validator.__name__), Codes.INFO)
            else:
                output(msgs.get_msg(e, lang, validator.__name__), Codes.ERROR)
                failed += 1
    
    if not failed:
        output(msgs.get_msg("CorrectResult", lang), Codes.CORRECT)
        
    return grader(failed)
