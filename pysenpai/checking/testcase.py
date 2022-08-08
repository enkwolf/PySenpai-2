import importlib
import inspect
import io
import sys

import pysenpai.callbacks.defaults as defaults
import pysenpai.callbacks.convenience as convenience
from pysenpai.exceptions import NoAdditionalInfo, NotCallable, OutputParseError
from pysenpai.output import json_output
from pysenpai.messages import load_messages, Codes
from pysenpai.output import output
from pysenpai.utils.internal import StringOutput, get_exception_line
from pysenpai.checking import TestCase

class TestCase(object):
    
    def __init__(self, ref_result, 
                 args=None,
                 inputs=None,
                 weight=1,
                 tag="",
                 validator=defaults.result_validator,
                 output_validator=None,
                 eref_results=None,
                 internal_config=None,
                 presenters=None):
                 
        self.args = args or []
        self.inputs = inputs or []
        self.weight = weight
        self.tag = tag
        self.ref_result = ref_result
        self.validator = validator
        self.output_validator = output_validator
        self.eref_results = eref_results or []
        self.correct = False
        self.output_correct = False
        self.internal_config = internal_config
        self.presenters = {
            "arg": defaults.default_value_presenter,
            "input": defaults.default_input_presenter,
            "ref": defaults.default_value_presenter,
            "res": defaults.default_value_presenter,
            "parsed": defaults.default_value_presenter,
            "call": defaults.default_call_presenter
        }
        if presenters:
            self.presenters.update(presenters)
    
    def configure_presenters(self, patch):
        self.presenters.update(patch)
    
    def present_object(self, category, value):
        return self.presenters[category](value)
        
    def present_call(self, target):
        return ""
    
    def feedback(self, res, parsed, output):
        for eref_result, msg_key in self.eref_results:
            try:
                self.validator(eref_result, res, parsed)
                yield (msg_key, {})
            except AssertionError:
                pass

    def parse(self, output):
        return output
    
    def validate_result(self, res, parsed, output):
        self.validator(self.ref_result, res, parsed)
        self.correct = True
    
    def validate_output(self, output):
        self.output_validator(output, self.args, self.inputs)
        self.output_correct = True
    
    def wrap(self, module, target):
        raise NotImplementedError

    def teardown(self):
        pass


class FunctionTestCase(TestCase):
    
    def present_call(self, target):
        return self.presenters["call"](target, self.args)
    
    def wrap(self, module, target):
        st_func = getattr(module, target)
        if not inspect.isfunction(st_func):
            raise NotCallable(name=target)
        return st_func(*self.args)


class ProgramTestCase(TestCase):
    
    def __init__(self, ref_result, 
                 args=None,
                 inputs=None,
                 weight=1,
                 tag="",
                 validator=convenience.parsed_result_validator,
                 output_validator=None,
                 eref_results=None,
                 internal_config=None,
                 presenters=None):
        
        super().__init__(
            ref_result, args, inputs, weight, tag, validator, output_validator, eref_results, internal_config, presenters
        )

    def wrap(self, module, target):
        importlib.reload(module)


class SnippetTestCase(TestCase):

    def wrap(self, module, target):
        pass



def run_test_cases(category, test_target, st_module, test_cases, lang, 
                  parent_object=None,
                  custom_msgs={},
                  hide_output=True,
                  test_recurrence=True,
                  validate_exception=False,
                  argument_cloner=defaults.default_argument_cloner,
                  new_test=defaults.default_new_test,
                  grader=defaults.pass_fail_grader): 



    # One time preparations
    save = sys.stdout
    msgs = load_messages(lang, category)
    msgs.update(custom_msgs)
    
    # call test and input producing functions 
    if inspect.isfunction(test_cases):
        test_cases = test_cases()
        
    # Show the name of the function
    # output(msgs.get_msg("FunctionName", lang).format(name=func_names[lang]), INFO)
    json_output.new_test(
        msgs.get_msg("TargetName", lang)["content"].format(name=test_target)
    )
    
    if parent_object is None:
        parent_object = st_module

    prev_res = None
    prev_out = None
    
    o = StringOutput()

    for i, test in enumerate(test_cases):
        json_output.new_run()

        try:
            inps = test.inputs
            sys.stdin = io.StringIO("\n".join([str(x) for x in inps]))
        except IndexError:
            inps = []

        if test.args:
            output(msgs.get_msg("PrintTestVector", lang), Codes.DEBUG,
                args=test.present_object("arg", test.args),
                call=test.present_call(test_target)
            )
        if test.inputs:
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG,
                inputs=test.present_object("input", test.inputs)
            )

        # Test preparations
        sys.stdout = o
        o.clear()

        # Calling the student function
        try:
            res = test.wrap(st_module, test_target)
        except NotCallable as e:
            sys.stdout = save
            output(msgs.get_msg("IsNotFunction", lang), ERROR, name=e.callable_name)
            return
        except Exception as e:
            if validate_exception:
                res = e
            else:
                sys.stdout = save
                etype, evalue, etrace = sys.exc_info()
                ename = evalue.__class__.__name__
                emsg = str(evalue)
                elineno, eline = get_exception_line(st_module, etrace)
                output(msgs.get_msg(ename, lang, default="GenericErrorMsg"), Codes.ERROR,
                    emsg=emsg,
                    ename=ename
                )
                output(msgs.get_msg("PrintExcLine", lang), Codes.DEBUG,
                    lineno=elineno, line=eline
                )
                test.teardown()
                continue
            
        # Validating function results
        sys.stdout = save
        if not hide_output:
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)

        try:
            st_out = test.parse(o.content)
        except OutputParseError as e:
            output(msgs.get_msg("OutputParseError", lang), Codes.INCORRECT,
                reason=str(e)
            )
            output(msgs.get_msg("OutputPatternInfo", lang), Codes.INFO)
            test.teardown()
            continue
            
        output(msgs.get_msg("PrintStudentResult", lang), Codes.DEBUG, 
            res=test.present_object("res", res),
            parsed=test.present_object("parsed", st_out),
            output=o.content
        )

        # Validate results
        try: 
            test.validate_result(res, st_out, o.content)
            output(msgs.get_msg("CorrectResult", lang), Codes.CORRECT)
        except AssertionError as e:
            # Result was incorrect
            output(msgs.get_msg(e, lang, "IncorrectResult"), Codes.INCORRECT)
            output(
                msgs.get_msg("PrintReference", lang),
                Codes.DEBUG,
                ref=test.present_object("ref", test.ref_result)
            )

            output(msgs.get_msg("AdditionalTests", lang), Codes.INFO)
                
            # Extra feedback
            for msg_key, format_args in test.feedback(res, st_out, o.content):
                output(msgs.get_msg(msg_key, lang), Codes.INFO, **format_args)

        if test.output_validator:
            try: 
                test.validate_output(o.content)
                output(msgs.get_msg("CorrectMessage", lang), Codes.CORRECT)
            except AssertionError as e:                
                output(msgs.get_msg(e, lang, "IncorrectMessage"), Codes.INCORRECT)
                output(msgs.get_msg("MessageInfo", lang), INFO)
                output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)
        
        test.teardown()
        prev_res = res
        prev_out = st_out
    
    return grader(test_cases)
