import inspect

def result_validator(ref, res, out):
    """
    This is the default validator function that provides reasonable validation
    for tests where the return values are either strings or integers, or 
    sequences containing similar simple types. The behavior provided by this 
    validator is direct comparison of values between the student result *res* and the
    reference result *ref*. 
    
    For convenience, string values are stripped of blanks before comparison and
    lists are converted to tuples. Sequence contents are not touched.
    """
    
    if isinstance(ref, str):
        ref = ref.strip()
    if isinstance(res, str):
        res = res.strip()
    if isinstance(ref, list):
        ref = tuple(ref)
    if isinstance(res, list):
        res = tuple(res)        
    assert res == ref

def default_pylint_validator(stats):
    """
    Default validator for pylint tests. Fails if score is less than 5. 
    """
    
    try:
        assert stats.global_note >= 5, "pylint_fail_low_score"
    except KeyError:
        raise AssertionError

def default_pylint_grader(stats):
    try:
        assert stats.global_note >= 9, "pylint_fail_low_score"
    except KeyError:
        raise AssertionError
    return 1

def default_value_presenter(value) -> str:
    """
    This is the default presenter for student result values, parsed results, reference values
    and function arguments. For simple values, repr is used to show the difference between 
    strings that are digits and actual numbers. One-dimensional lists and tuples are presented
    using repr for each invidual item and items are separated with spaces. Dictionary items are 
    presented as :code:`"{}: {}"` where repr of both key and value are used.    
    
    For more precise control of representing more complex structures, a custom presenter is
    recommended.
    """    
    
    if isinstance(value, (list, tuple)):
        return " ".join([repr(x) for x in value])
    elif isinstance(value, dict):
        return "\n" + "\n".join(["{}: {}".format(repr(k), repr(v)) for k, v in value.items()])
    else:
        return repr(value)
    
def default_input_presenter(value) -> str:
    """
    This is the default presenter for input vectors. Individual inputs are separated by spaces
    and they are shown using str instead of repr. 
    """
    
    return "{{{\n" + "\n".join([str(x) for x in value]) + "\n}}}"
    
def default_call_presenter(func_name, args) -> str:
    """
    This function is used for showing the way the student function was called
    during a test. It forms a function call code line using the function name 
    and its arguments. If the call would be long (over 80 characters), it is 
    split to multiple lines. 
    """
    
    call = func_name + "("
    if len(str(args)) > 80:
        call += "\n"
        call += ",\n".join("    " + repr(arg) for arg in args)
        call += "\n)"
    else:
        call += ", ".join(repr(arg) for arg in args)
        call += ")"
    
    return "{{{highlight=python3\n" + call + "\n}}}"
    
    
def default_vars_presenter(module) -> str:
    """
    Default presenter for student module variables in code snippet tests. 
    """
    
    var_vals = ""
    for name in sorted(module.__dict__.keys()):
        if not name.startswith("_"):
            value = getattr(module, name)
            if not inspect.ismodule(value) and not inspect.isfunction(value):
                if isinstance(value, list) and len(str(value)) > 80:
                    var_vals += "{} = [\n    ".format(name) 
                    var_vals += repr(value)[1:-1].replace("], ", "],\n    ") 
                    var_vals += "\n]\n"
                else:
                    var_vals += "{} = {}\n".format(name, repr(value))
        
    return "{{{highlight=python3\n" + var_vals + "\n}}}"
    
    
def pass_fail_grader(test_cases):
    return int(all(case.correct for case in test_cases))
    
def static_pass_fail_grader(failed):
    return int(not failed)
    
def default_construct_presenter(code) -> str:
    """
    Default presenter for code constructed around the student's answer in a
    code snippet test.
    """
    
    return "{{{highlight=python3\n" + code + "\n}}}"

def default_parser(out) -> str:
    """
    This is a dummy output parser that is used as the default. It is usable in tests where
    output is not evaluated. 
    """
    
    return out
    
def default_message_validator(out, args, inputs):
    """
    This dummy validator is used as the default message validator. It is usable in tests where
    messages are not evaluated.
    """
    
    pass
    
def default_argument_cloner(args):
    """
    Dummy cloner to be used as the default. Used whenever there is no need to clone the 
    argument vector. 
    """
    
    return args

def default_new_test(args, inputs):
    """
    Default actions to take at the start of each individual test case. The default action is
    to do nothing.
    """
    
    pass

default_presenters = {
    "arg": default_value_presenter,
    "input": default_input_presenter, 
    "ref": default_value_presenter,
    "res": default_value_presenter,
    "parsed": default_value_presenter,
    "call": default_call_presenter,
    "vars": default_vars_presenter,
    "ref_vars": default_vars_presenter
}
