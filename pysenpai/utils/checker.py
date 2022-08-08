import inspect
import random
import re
from pysenpai.exceptions import NoMatchingObject

import_as_pat = re.compile("import (?P<module>[A-Za-z0-9_]+) as (?P<alias>[A-Za-z0-9_ÄäÖö]+)")

class CallLogger(object):

    def __init__(self):
        self.calls = []
        self.args = []
        self.kwargs = []

    def __call__(self, *args, **kwargs):
        self.args.append(args)
        self.kwargs.append(kwargs)
        
    def __getattr__(self, attr):
        self.calls.append(attr)
        return self
        
    def __iter__(self):
        for call, args, kwargs in zip(self.calls, self.args, self.kwargs):
            yield call, args, kwargs

class SimpleRef(object):
    """
    This object simulates a module for code snippet tests. When created,
    attributes can be set to be compared with the student module.
    """
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    
    def __call__(self, inputs):        
        return self

def find_first(pattern, string, rtype=str):
    """
    find_first(pattern, string[, rtype=str]) -> value
    
    Find the first match in *string* using compiled regular expression *pattern*. 
    If found, the match is converted into *rtype* before it's returned. If not found,
    returns None.    
    """
    
    try:
        return rtype(pattern.findall(string)[0])
    except IndexError:
        return None

def find_objects(st_module, object_type, first=True, name_only=False, exclude=None):
    """
    find_objects(st_module, object_type[, first=True][, name_only=False]) -> string or list
    
    Finds object(s) that are instance of the given type from the student code
    module. If *first* is True, only returns one object (list otherwise) and if
    *name_only* is True, returns name of the object (which can be used with
    setattr to assign a new value to the same name).
    
    This utility function is useful for exercises where checker needs to access
    a member of the student's code module, but its name has not been specified
    in the assignment. 
    """
    
    matches = []
    exclude = exclude or []
    
    for name in dir(st_module):
        if not name.startswith("_") and name not in exclude:
            if isinstance(getattr(st_module, name), object_type):
                if first:
                    if name_only:
                        return name
                    else:
                        return getattr(st_module, name)
                else:
                    if name_only:
                        matches.append(name)
                    else:
                        matches.append(getattr(st_module, name))
    else:
        if matches:
            return matches
        else:
            raise NoMatchingObject

def replace_module(st_module, module_name, object):
    for match in import_as_pat.finditer(inspect.getsource(st_module)):
        if match.group("module") == module_name:
            module_name = match.group("alias")
    setattr(st_module, module_name, object)

def determine_question(history, completed, active, target):
    '''
    Determines what and if a question needs to be asked. 
    - Depends on cmd line argument and the amount of correct questions answered.
    '''
    if completed:
        return random.choice(active), None, None

    choices = []
    remaining = 0
    done = 0
    for cq in active:
        correct = history.count([cq, True])
        incorrect = history.count([cq, False])
        done += correct
        if correct < target or correct <= incorrect:
            choices.append(cq)
            remaining += max(target - correct, incorrect - correct)

    return random.choice(choices), done, done + remaining
