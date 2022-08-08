import argparse
import atexit
import importlib
import io
import json
import os.path
import sys
from stdlib_list import stdlib_list
import pysenpai.callbacks.defaults as defaults
from pysenpai.output import json_output
from pysenpai.messages import load_messages, Codes 
from pysenpai.output import output
from pysenpai.utils.internal import FNAME_PAT, CommaSplitAction, StringOutput, get_exception_line

# expose basic checking interface through this module
from pysenpai.messages import TranslationDict
from pysenpai.checking.program import test_program
from pysenpai.checking.snippet import test_code_snippet
from pysenpai.checking.function import test_function, FunctionTestCase
from pysenpai.checking.static import static_test
from pysenpai.checking.lint import pylint_test


def end():
    """
    This function gets called automatically when this module exits. It prints
    the JSON document into stdout.
    
    You can pipe the output to the cli_print script to get a more readable 
    representation when testing checkers in a command line interface.
    """
        
    print(json.dumps(json_output))
    
atexit.register(end)

def init_test(name, max_score):
    """
    Sets the tester name. Call this is in the checker if you need the checker's
    file name included in the output JSON document.
    """
    
    json_output.set_tester(name)
    json_output.set_max_score(max_score)

def set_result(correct, score):
    json_output.update_result(correct, score)


def parse_command():
    """
    parse_command() -> list, str
    
    This parses the checker command for files to test and testing language. Available
    arguments are:
    
    * -l --lang --locale : sets the checker language using language codes
    * -q --questions : enabled question types (integers) as comma-separated string
    * -c --check : check a routine exercise answer (and generate another)
    * -r --request : request new routine exercise instance
    
    Everything else is considered as files to test.

    Returns all files' basenames as a list and the language as a separate value.
    
    If the files are located in subfolders, adds the folders to the path. This makes them
    importable later.
    
    When writing checkers, this is typically the first function to call. 
    """
    
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="filename", nargs="*", help="file(s) to test")
    parser.add_argument(
        "-l", "--locale", "--lang",
        dest="lang",
        default="en",
        help="locale to use for running the test"
    )
    parser.add_argument(
        "-q" "--questions",
        action=CommaSplitAction,
        dest="questions",
        default="",
        help="list of comma separated question classes to choose from"
    )

    parser.add_argument(
        "-c", "--check", 
        action="store_const",
        dest="check",
        const=True,
        default=False,
        help="checking a grind session"
    )
    parser.add_argument(
        "-r", "--request-params", 
        action="store_const",
        dest="request",
        const=True,
        default=False,
        help="command is a request for params"
    )
    parser.add_argument(
        "-t", "--target",
        type=int,
        dest="target",
        default=1,
        help="target amount of correct answers for routine exercise"
    )
    
    args = parser.parse_args()
    if args.request or args.check:
        with open(args.files[0]) as s:
            return json.load(s), args

    for i, path in enumerate(args.files):
        if os.path.dirname(path):
            sys.path.insert(0, os.path.dirname(path))
        #args.files[i] = os.path.basename(path)
    
    return args.files, args.lang    

# NOTE: custom_msgs, inputs are read only
# therefore setting defaults to empty lists / dictionaries is safe here. 
def load_module(module_path, 
                lang="en", 
                custom_msgs={}, 
                inputs=[], 
                hide_output=True, 
                allow_output=True, 
                presenter=defaults.default_input_presenter):
    """
    load_module(module_path[, lang="en"][, custom_msgs={}][, inputs=[]][, hide_output=True][, allow_output=True][, presenter=default_input_presenter]) -> Module
    
    This function imports the student module and needs to be called before doing tests.
    The parameters are
    
    * *lang* - language for messages
    * *custom_msgs* - a TranslationDict object that includes additions/overrides 
      to the default import messages
    * *inputs* - input vector to be given to the program; inputs are automatically joined 
      by newlines and made into a StringIO object that replaces standard input. When 
      calling this function you need to provide inputs that allow the program to execute
      without errors. 
    * *hide_output* - a flag to hide or show output, by default output is hidden
    * *allow_output* - a flag that dictates whether it's considered an error if the code
      has output or not. By default output is allowed.
    * *presenter* - a presenter function for showing inputs in the output in case of
      errors
       
    Before attempting to import the student module, the function checks whether the 
    filename is a proper Python module name. None is returned if the filename is
    invalid. This also happens if the module has the same name as a Python library module.
    
    If importing the student module results in an exception, the exception's name is
    looked up from the message dictionary and the corresponding error message is
    shown in the checker output. If the exception name is not found, GenericErrorMsg
    is shown instead. See :ref:`Output Messages <output-messages>` for information
    about how to specify your own error messages. 
    
    If importing is successful and *allow_output* is set to False, the StringOutput
    object is checked for prints and an error message is given if content is found.
    Otherwise the module object is returned.    
    """

    save = sys.stdout
    msgs = load_messages(lang, "import")
    msgs.update(custom_msgs)
    
    module_name = os.path.basename(module_path)
    
    json_output.new_test(msgs.get_msg("LoadingModule", lang)["content"].format(name=module_name))
    json_output.new_run()
    
    if not module_name.endswith(".py"):
        output(msgs.get_msg("MissingFileExtension", lang), Codes.ERROR)
        return None

    name = module_name.rsplit(".py", 1)[0]
    if not FNAME_PAT.fullmatch(name):    
        output(msgs.get_msg("BadModuleName", lang), Codes.ERROR, name=module_name)
        return None
        
    pyver = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
        
    if name in stdlib_list(pyver):
        output(msgs.get_msg("SystemModuleName", lang), Codes.ERROR, name=module_name)
        return None
        
    if inputs:
        sys.stdin = io.StringIO("\n".join([str(i) for i in inputs]))
        
    o = StringOutput()
    sys.stdout = o
    
    try:        
        st_module = importlib.import_module(name)
    except:
        sys.stdout = save
        etype, evalue, etrace = sys.exc_info()
        ename = evalue.__class__.__name__
        emsg = str(evalue)
        #elineno, eline = get_exception_line(st_module, etrace)
        output(msgs.get_msg(ename, lang, default="GenericErrorMsg"), Codes.ERROR, 
            ename=ename, emsg=emsg, inputs=presenter(inputs)
        )
        if inputs:
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=presenter(inputs))
    else:
        sys.stdout = save
        if not allow_output and o.content:
            output(msgs.get_msg("DisallowedOutput", lang), Codes.ERROR, output=o.content)
        elif not hide_output:
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.DEBUG, output=o.content)
            
        return st_module

