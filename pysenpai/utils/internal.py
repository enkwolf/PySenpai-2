import argparse
import re

FNAME_PAT = re.compile("[a-zA-Z0-9_]+")

class StringOutput(object):
    """
    This class is used as a replacement for sys.stdout whenever the student code
    is running. It saves the output into a string so that it can be parsed and/or 
    evaluated in the evaluation phase of the test. 
    """    
    
    errors = ""
    encoding = "utf-8"
    
    def __init__(self):
        self.content = ""
    
    def write(self, text):
        """
        Write into the contained string.
        """
        
        self.content += text
        
    def clear(self):
        """
        Clear the contained string.
        """
        
        self.content = ""
        
    def flush(self):
        """
        Required to exist for file-like objects, doesn't need to do anything.
        """
        
        pass


class CommaSplitAction(argparse.Action):
    """
    Action class for argument parsing. Takes a comma separated string and
    returns the split result as integers. Used in routine exercise parsing with
    the argument that chooses question types to use.
    """
    
    def __call__(self, parser, namespace, values, options=None):
        setattr(namespace, self.dest, [int(v) for v in values.split(",")])


def reset_locals(module):
    """
    This function ensures that the student module is clean after each execution.
    It deletes all names from the *module*'s namespace. The reason for this procedure
    is that occasionally students return programs where all names are not set on 
    every run. When the code is run normally these scenarios would result in 
    UnboundLocalError. However, if the name was successfully set on the first run
    but is not set on the second run, the value from the first run is retained when
    using importlib.reload. This results in weird errors that are avoided when all 
    locals are nuked from the orbit before reloading the module. 
    """
    
    m_locals = [name for name in dir(module) if not name.startswith("__")]
    for name in m_locals:
        delattr(module, name)
    
def walk_trace(tb, tb_list):    
    """
    Turns the stack traceback into a list by recurring through it. 
    """
    
    tb_list.append(tb)
    if tb.tb_next:
        walk_trace(tb.tb_next, tb_list)

def get_exception_line(module, etrace):
    """
    This function goes through a traceback and finds the last line of code from 
    within *module* that was involved in causing the exception. This function 
    is used whenever there is an exception to show the student which line of 
    their code caused it. After getting the line number from the traceback, 
    the function finds the corresponding line from the student's code file and
    returns it alongside the line number.
    
    If no line is found, it returns ? for the line number and nothing for the 
    line itself - this usually occurs when the student's function definition 
    doesn't match the expected one, resulting in a TypeError. 
    """
    
    tb_list = []
    try:
        walk_trace(etrace, tb_list)
    except RecursionError:
        pass
    #for tb in tb_list:
    #    print(tb.tb_frame.f_code.co_filename)
    try:
        st_last_frame = [tb.tb_frame for tb in tb_list if tb.tb_frame.f_code.co_filename == module.__file__][-1]
    except IndexError:
        return "?", ""
        
    with open(module.__file__) as cf:
        for i in range(st_last_frame.f_lineno):
            code = cf.readline()
        return st_last_frame.f_lineno, code.strip()
