import inspect
import io
import sys

import pysenpai.callbacks.defaults as defaults
from pysenpai.output import json_output
from pysenpai.messages import load_messages, Codes
from pysenpai.output import output
from pysenpai.utils.internal import StringOutput, get_exception_line


# NOTE: custom_msgs, inputs, error_refs, custom_tests, info_funcs are read only
# therefore setting defaults to empty lists / dictionaries is safe here. 
def test_function(st_module, func_names, test_vector, ref_func,
                  lang="en",
                  parent_object=None,
                  custom_msgs={},
                  inputs=[],
                  hide_output=True,
                  test_recurrence=True,
                  ref_needs_inputs=False,
                  error_refs=[],
                  custom_tests=[],
                  info_funcs=[],
                  validator=defaults.result_validator,
                  presenter=defaults.default_presenters,
                  output_parser=defaults.default_parser,
                  message_validator=None,
                  validate_exception=False,
                  result_object_extractor=None,
                  argument_cloner=defaults.default_argument_cloner,
                  repeat=1,
                  new_test=defaults.default_new_test): 
    """
    test_function(st_module, func_names, test_vector, ref_func[, lang="en"][, kwarg1][, ...])
    
    Tests a student function with a set of test vectors, against a reference 
    function. The behavior of this function can be customized heavily by using 
    callbacks and other optional keyword arguments. All arguments are listed and
    explained below. 
    
    * *st_module* - a module object that contains the function that's being tested
    * *func_names* - a dictionary that has two character language codes as keys and
      corresponding function name in that language as values
    * *test_vector* - a list of argument vectors or a function that generates the 
      the list. This vector must be sequences within a list, where each sequence 
      is one test case. Each case vector is unpacked when reference and student 
      functions are called.
    * *ref_func* - reference function that gets called with the same arguments as
      the student function to obtain the reference result for each test case.
    * *lang* - language for messages and for finding the student function
    * *custom_msgs* - a TranslationDict object that includes additions/overrides 
      to the default function test messages
    * *inputs* - input vectors to be given to the function; must have as many vectors 
      as test_vector. Inputs are automatically joined by newlines and made into a 
      StringIO object that replaces standard input. Necessary when testing functions 
      that accept user input.
    * *hide_output* - a flag to show/hide student function prints in the test 
      output. By default student output is hidden. 
    * *test_recurrence* - a flag to enable/disable a convenience test that checks
      if the student code repeatedly returns the same result regardless of 
      arguments/inputs given to the function. Default is True. Should be disabled
      for functions that don't return anything to avoid confusing messages.
    * *ref_needs_inputs* - if set to True, the reference function is given two 
      lists instead of unpacking the argument vector for each case. In this case 
      the reference function is always called with exactly two parameters: list of 
      arguments and list of inputs. Default is False. This behavior is necessary if
      your reference function needs to change its result based on inputs. 
    * *error_refs* - a list of false reference functions that will be called if the
      student function output does not match the true reference. These are useful
      for exposing common implementation errors. See 
      :ref:`Providing Debug Information <debug-information>` for more about these 
      functions. 
    * *custom_tests* - a list of test functions that are called if the test is failed. 
      These tests can examine any of the test parameters and raise AssertionError if 
      problems are detected. See :ref:`Providing Debug Information <debug-information>` 
      for more about these functions. 
    * *info_funcs* - a list of information functions that are called if the test fails.
      These are similar to custom tests, but instead of making asserts, they should 
      return a value that is shown in the corresponding output message. See 
      :ref:`Providing Debug Information <debug-information>` for more about these 
      functions. 
    * *validator* - the function that performs the validation of the student function
      return value and/or parsed output against the reference. Validators must use 
      assert. The assert's error message is used to retrieve a message from the 
      dictionary to show in the output as the test result in case of failure.
    * *presenter* - a dictionary with any or all of the following keys: arg, call,
      input, ref, res, parsed. Each key must be paired with a function that returns
      a string. These functions are used to make data structures cleaner in the output.
      See section :ref:`Presenters <presenters>` for more information.
    * *output_parser* - a function that retrieves data by parsing the student 
      function's output. Values obtained by the parser are offered separately from 
      the function's return values to the validator. Output parsers can abort the 
      test case by raising OutputParseError.
    * *message_validator* - a function that validates the student function's raw 
      output (as opposed to parsing values from it). This validation is done 
      separately from the main validator function. Like the validator, it must use
      assert, and the assert's error message is used to retrieve a message to show. 
      If omitted, no message validation will be performed.
    * *result_object_extractor* - a function that returns a result object that is 
      to be used in validation instead of the student function's return value. The
      object can be selected from the argument vector, return value(s) or parsed 
      values. If not set, this process will be skipped. Useful for testing functions
      that modify a mutable object. 
    * *argument_cloner* - a function that makes a copy of the argument vector for 
      two purposes: calling the reference without contaminating a mutable object 
      in the arguments; and being able to show the original state of the argument
      vector after the student function has been called. Usually needed for testing 
      functions that modify mutable objects. 
    * *repeat* - sets the number of times to call the student function before doing
      the evaluation. Default is 1. 
    * *new_test* - a function that is called at the start of each test case. Can be
      used to reset the state of persistent objects within the checker. Receives 
      arguments and inputs when called.
    
    Test progression is divided into two steps: one-time preparations and actual 
    test cases. One-time preparations proceed as follows.
    
    #. The handle to the original sys.stdout is saved so that it can be restored 
       later
    #. The messages dictionary is updated with messages received in the custom_msgs
       parameter
    #. Presenter functions are set for different categories
    #. If arguments and inputs are provided as functions, they are called
    #. Output is redirected to a StringOutput object
    #. Test cases are prepared by obtaining the reference result for each test 
       case - i.e. all reference results are obtained before running any tests
       before the student code has a chance to mess with things 
       
    The number of test cases is determined from the length of the test vector. Even if 
    the tested function takes no arguments, your test vector must contain an empty list
    for each test case! 
    
    Each test case is processed as follows. During the test, sys.stdout is restored
    whenever a message is shown to the student.
    
    #. new_test callback is called
    #. Stored output is cleared and output is redirected to the StringOutput object
    #. If there are inputs, a StringIO object is formed to replace sys.stdin
    #. A copy of arguments is made using argument_cloner
    #. The student function is called
    
       * If there is an error, the appropriate error message is retrieved from the 
         dictionary. Arguments and inputs (if present) are also shown in the output.
         Testing proceeds to the next case.
    
    #. If hide_output is False, the student output is shown in the evaluation 
    #. The student function output is parsed
    
       * If there is an error, OutputParseError message is shown along with 
         OutputPatternInfo. Arguments and inputs (if present) are also shown in the 
         evaluation output. Testing proceeds to the next case. 
         
    #. If result_object_extractor has been, the student function's return value
       is replaced by the callback's return value. 
    #. The validator is called
    
       * Regardless of outcome, arguments, inputs and student result are always shown.
       * If succcessful, the CorrectResult message is shown in the output.
       * If unsuccessful, the following steps are taken to provide more information.
       
         #. A message explaining the problem is shown, along with the reference result
         #. False reference functions are called and validated against the student
            result. A message corresponding to the function name is shown if
            the validation is a match. 
         #. Custom test functions are called and appropriate messages are shown if
            they raise AssertionErrors. 
         #. If test_recurrence is True, a message is printed if the student function
            returned the same result as the last test.
         #. Information functions are called and their corresponding messages are
            shown in the output, including the information function's return value.
             
    #. If test_messages is True, message_validator is called.
    
       * If successful, the CorrectMessage message is shown in the output.
       * If unsuccessful, a message explaining the problem is shown along with 
         the MessageInfo message and the student function's raw output.
    """
    
    # One time preparations
    save = sys.stdout
    msgs = load_messages(lang, "function")
    msgs.update(custom_msgs)
    
    # Set specific presenters to use generic presenter if not given
    if isinstance(presenter, dict):
        arg_presenter = presenter.get("arg", defaults.default_value_presenter)
        input_presenter = presenter.get("input", defaults.default_input_presenter)
        ref_presenter = presenter.get("ref", defaults.default_value_presenter)
        res_presenter = presenter.get("res", defaults.default_value_presenter)       
        parsed_presenter = presenter.get("parsed", defaults.default_value_presenter)
        call_presenter = presenter.get("call", defaults.default_call_presenter)
    else:        
        arg_presenter = presenter
        input_presenter = presenter
        ref_presenter = presenter
        res_presenter = presenter
        parsed_presenter = presenter
        call_presenter = presenter
    
    # call test and input producing functions 
    if inspect.isfunction(test_vector):
        test_vector = test_vector()
        
    if inspect.isfunction(inputs):
        inputs = inputs()
            
    # Show the name of the function
    #output(msgs.get_msg("FunctionName", lang).format(name=func_names[lang]), INFO)
    json_output.new_test(
        msgs.get_msg("FunctionName", lang)["content"].format(name=func_names[lang])
    )
    
    # Redirect output to string-like object
    o = StringOutput()
    sys.stdout = o
            
    # Prepare test cases. Each case is comprised of its vectors and the reference result 
    tests = []
    if ref_needs_inputs:
        test_vector = zip(test_vector, inputs)
        for v, i in test_vector:
            tests.append((v, ref_func(argument_cloner(v), i)))
    else:        
        for v in test_vector:
            tests.append((v, ref_func(*argument_cloner(v))))
    
    prev_res = None
    prev_out = None
    
    # Running tests
    if parent_object is None:
        parent_object = st_module
    
    for i, test in enumerate(tests):
        json_output.new_run()

        # Test preparations
        args, ref = test
        sys.stdout = o
        o.clear()

        new_test(argument_cloner(args), inputs)

        try:
            inps = inputs[i]
            sys.stdin = io.StringIO("\n".join([str(x) for x in inps]))            
        except IndexError:
            inps = []

        stored_args = argument_cloner(args)

        # Calling the student function
        try:
            st_func = getattr(parent_object, func_names[lang])
            if inspect.isfunction(st_func) or inspect.ismethod(st_func) or inspect.isclass(st_func):
                for i in range(repeat):
                    res = st_func(*args)
            else:
                sys.stdout = save
                output(msgs.get_msg("IsNotFunction", lang), Codes.ERROR, name=func_names[lang])
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
                    args=arg_presenter(stored_args),
                    inputs=input_presenter(inps),
                    emsg=emsg,
                    ename=ename
                )
                output(msgs.get_msg("PrintExcLine", lang), Codes.DEBUG,
                    lineno=elineno, line=eline
                )
                output(msgs.get_msg("PrintTestVector", lang), Codes.DEBUG,
                    args=arg_presenter(stored_args),
                    call=call_presenter(func_names[lang], stored_args)
                )
                if inputs:
                    output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG,
                        inputs=input_presenter(inps)
                    )

                continue
            
        # Validating function results
        sys.stdout = save
        values_printed = False
        if not hide_output:
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)

        try:
            st_out = output_parser(o.content)
        except OutputParseError as e:
            output(msgs.get_msg("OutputParseError", lang), Codes.INCORRECT,
                args=arg_presenter(stored_args),
                inputs=input_presenter(inps),
                output=o.content,
                reason=str(e)
            )
            output(msgs.get_msg("PrintTestVector", lang), Codes.DEBUG, 
                args=arg_presenter(stored_args), 
                call=call_presenter(func_names[lang], stored_args)
            )
            if inputs:
                output(
                    msgs.get_msg("PrintInputVector", lang),
                    Codes.DEBUG,
                    inputs=input_presenter(inps)
                )
            output(msgs.get_msg("OutputPatternInfo", lang), Codes.INFO)
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)
            continue
            
        # The evaluated result must include an object that was changed during the function call
        if result_object_extractor:
            res = result_object_extractor(args, res, st_out)
            
        # Validate results
        try: 
            validator(ref, res, st_out)
            output(msgs.get_msg("CorrectResult", lang), Codes.CORRECT)
        except AssertionError as e:
            # Result was incorrect
            output(msgs.get_msg(e, lang, "IncorrectResult"), Codes.INCORRECT)
            output(msgs.get_msg("PrintTestVector", lang), Codes.DEBUG,
                args=arg_presenter(stored_args),
                call=call_presenter(func_names[lang], stored_args)
            )
            if inputs:
                output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, 
                    inputs=input_presenter(inps)
                )
            output(msgs.get_msg("PrintStudentResult", lang), Codes.DEBUG, 
                res=res_presenter(res),
                parsed=parsed_presenter(st_out),
                output=o.content
            )
            output(msgs.get_msg("PrintReference", lang), Codes.DEBUG, ref=ref_presenter(ref))
            values_printed = True
            if error_refs or custom_tests or test_recurrence:
                output(msgs.get_msg("AdditionalTests", lang), Codes.INFO)
                
            # Run false references
            for eref_func in error_refs:
                if ref_needs_inputs:
                    eref = eref_func(argument_cloner(stored_args), inps)
                else:
                    eref = eref_func(*argument_cloner(stored_args))
                try: 
                    validator(eref, res, st_out)
                    output(msgs.get_msg(eref_func.__name__, lang), Codes.INFO)
                except AssertionError as e:
                    pass
                    
            # Run custom tests
            for custom_test in custom_tests:
                try: 
                    custom_test(res, st_out, o.content, ref, stored_args, inps)
                except AssertionError as e:
                    output(msgs.get_msg(e, lang, custom_test.__name__), Codes.INFO)
            
            # Result recurrence test
            if test_recurrence and (res == prev_res or st_out and st_out == prev_out):
                output(msgs.get_msg("RepeatingResult", lang), Codes.INFO)
            
            # Run info functions
            if info_funcs:
                output(msgs.get_msg("AdditionalInfo", lang), Codes.INFO)
                for info_func in info_funcs:
                    try:
                        output(msgs.get_msg(info_func.__name__, lang), Codes.INFO,
                            func_res=info_func(res, st_out, o.content, ref, stored_args, inps)
                        )
                    except NoAdditionalInfo:
                        pass
        else:
            # Result was correct
            output(msgs.get_msg("PrintTestVector", lang), Codes.DEBUG,
                args=arg_presenter(stored_args),
                call=call_presenter(func_names[lang], stored_args)
            )
            if inputs:
                output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG,
                    inputs=input_presenter(inps)
                )
            output(
                msgs.get_msg("PrintStudentResult", lang),
                Codes.DEBUG,
                res=res_presenter(res),
                parsed=parsed_presenter(st_out),
                utput=o.content
            )
            values_printed = True
                
        # Validate student output    
        if message_validator:
            try: 
                message_validator(o.content, stored_args, inps)
                output(msgs.get_msg("CorrectMessage", lang), Codes.CORRECT)
            except AssertionError as e:                
                output(msgs.get_msg(e, lang, "IncorrectMessage"), Codes.INCORRECT)
                output(msgs.get_msg("MessageInfo", lang), INFO)
                output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)
                if not values_printed:
                    output(msgs.get_msg("PrintTestVector", lang), Codes.DEBUG,
                        args=arg_presenter(stored_args),
                        inputs=input_presenter(inps),
                        call=call_presenter(func_names[lang], stored_args)
                    )
                    if inputs:
                        output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG,
                            inputs=input_presenter(inps)
                        )
        
        prev_res = res
        prev_out = st_out
