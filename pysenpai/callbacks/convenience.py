def rounding_float_result_validator(ref, res, out):
    """
    This is a convenience callback for validating functions that return floating
    point values. Values are rounded to two decimal precision in order to account 
    for precision error caused by different implementations. The function compares
    student result *res* against the reference result *ref*. 
    """
    
    if isinstance(res, float):
        assert round(res, 2) == round(ref, 2)
    else:
        raise AssertionError
    
def parsed_list_validator(ref, res, out):
    """
    This is a convenience callback for validating lists of parsed results against 
    a reference list. The comparison of *out* to *ref* is done item by item as opposed 
    to the default validator (which compares *res*). Comparison is done item to item.
    """
    
    try:
        for i, v in enumerate(ref):
            assert v == out[i]
    except IndexError:
        raise AssertionError
    
def parsed_result_validator(ref, res, out):
    """
    This is the default validator for program tests, and a convenience callback for
    validating functions that print simple values. It compares the values parsed from
    student output *out* to values returned by the reference function *ref*. 
    
    Similar to the default validator, strings are stripped of blanks before comparison
    and lists are converted to tuples. Sequence contents are not touched. 
    """
    
    if isinstance(ref, str):
        ref = ref.strip()
    if isinstance(out, str):
        out = out.strip()
    if isinstance(ref, list):
        ref = tuple(ref)
    if isinstance(out, list):
        out = tuple(out)        
    assert out == ref
 
def vars_validator(ref, res, out):
    """
    Default validator for code snippet tests. Compares variable names and values
    found within the executed student module and the reference object.
    """
    
    for name in ref.__dict__.keys():
        if not name.startswith("_"):
            assert hasattr(res, name), "fail_missing_variable"
            assert getattr(res, name) == getattr(ref, name), "fail_variable_value"

def strict_pylint_validator(stats):
    try:
        assert stats["global_note"] >= 10, "pylint_fail_low_score"
    except KeyError:
        raise AssertionError
        
def raw_presenter(value) -> str:
    """
    This is the simplest presenter that simply returns the repr form of a *value*. 
    """
    
    return repr(value)
    
def output_bonus_grader(test_cases):
    functional = all(case.correct for case in test_cases)
    if functional:
        return 1 + int(all(case.output_correct for case in test_cases))
    return 0
