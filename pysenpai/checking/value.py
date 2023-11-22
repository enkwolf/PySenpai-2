import inspect
import sys
import pysenpai.callbacks.defaults as defaults
from pysenpai.output import json_output
from pysenpai.messages import load_messages, Codes
from pysenpai.output import output
from pysenpai.utils.internal import StringOutput, get_exception_line

class ValueTestCase:

    def __init__(self, ref_result,
                 weight=1,
                 tag="",
                 validator=defaults.result_validator,
                 eref_results=None,
                 internal_config=None,
                 presenters=None):

        self.weight = weight
        self.tag = tag
        self.ref_result = ref_result
        self.validator = validator
        self.eref_results = eref_results or []
        self.correct = False
        self.internal_config = internal_config
        self.presenters = {
            "ref": defaults.default_value_presenter,
            "res": defaults.default_value_presenter,
        }

    def wrap(self, st_value, target):
        return st_value

    def validate_result(self, res, parsed, output):
        self.validator(self.ref_result, res, parsed)
        self.correct = True

    def present_object(self, category, value):
        return self.presenters[category](value)

    def teardown(self):
        pass

    def feedback(self, res, parsed, output):
        for eref_result, msg_key in self.eref_results:
            try:
                self.validator(eref_result, res, parsed)
                yield (msg_key, {})
            except AssertionError:
                pass


def value_test(st_value, test_cases, lang,
               msg_module="pysenpai",
               custom_msgs={},
               grader=defaults.pass_fail_grader):

    msgs = load_messages(lang, "value", module=msg_module)
    msgs.update(custom_msgs)

    if inspect.isfunction(test_cases):
        test_cases = test_cases()

    json_output.new_test(
        msgs.get_msg("TargetName", lang)["content"].format(name="")
    )

    for i, test in enumerate(test_cases):
        json_output.new_run()
        try:
            res = test.wrap(st_value, None)
        except BaseException:
            etype, evalue, etrace = sys.exc_info()
            ename = evalue.__class__.__name__
            emsg = str(evalue)
            output(msgs.get_msg(ename, lang, default="GenericErrorMsg"), Codes.ERROR,
                emsg=emsg,
                ename=ename
            )
            test.teardown()
            continue

        output(msgs.get_msg("PrintStudentResult", lang), Codes.DEBUG,
            res=test.present_object("res", res),
            parsed="",
            output=""
        )

        try:
            test.validate_result(res, None, None)
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
            for msg_key, format_args in test.feedback(res, None, None):
                output(msgs.get_msg(msg_key, lang), Codes.INFO, **format_args)

        test.teardown()

    return grader(test_cases)




