import importlib
import inspect
import io
import sys

import pysenpai.callbacks.defaults as defaults
import pysenpai.callbacks.convenience as convenience
from pysenpai.exceptions import OutputParseError
from pysenpai.messages import load_messages, Codes
from pysenpai.output import json_output, output
from pysenpai.utils.internal import StringOutput, get_exception_line, reset_locals


# NOTE: custom_msgs, error_refs, custom_tests, info_funcs are read only
# therefore setting defaults to empty lists / dictionaries is safe here. 
def test_program(st_module, test_vector, ref_func,
                 lang="en",
                 custom_msgs={},
                 hide_output=True,
                 test_recurrence=True,
                 error_refs=[],
                 custom_tests=[],
                 info_funcs=[],
                 validator=convenience.parsed_result_validator,
                 presenter=defaults.default_presenters,
                 output_parser=defaults.default_parser,
                 message_validator=None,
                 new_test=defaults.default_new_test):
    """
    test_program(st_module, test_vector, ref_func[, lang="en"][, kwarg1][, ...])
    
    Tests student's main program using a set of test vectors, against a reference 
    function that emulates the desired behavior. Due to the nature of this 
    function's implementation, the student main program cannot be tested if it is
    placed inside :code:`if __name__ == "__main__":`. Overall the test procedure
    is simpler than function testing because there are no arguments to pass - 
    only inputs. 
    
    * *st_module* - a module object that's being tested
    * *test_vector* - input vectors to be given as inputs; Inputs are automatically 
      joined by newlines and made into a StringIO object that replaces standard
      input.
    * *ref_func* - reference function that is given the input vector as arguments
      and should return values that match what is expected from the student program. 
      It should **not** consume inputs (i.e. don't call :func:`input`).
    * *lang* - language for messages
    * *custom_msgs* - a TranslationDict object that includes additions/overrides 
      to the default program test messages
    * *hide_output* - a flag to show/hide student program prints in the test 
      output. By default student output is hidden. 
    * *test_recurrence* - a flag to enable/disable a convenience test that checks
      if the student code repeatedly prints the same result regardless of inputs 
      given. Default is True. 
    * *error_refs* - a list of false reference functions that will be called if the
      student program output does not match the true reference. These are useful
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
    * *validator* - the function that performs the validation of the student program
      parsed output against the reference. Validators must use assert. The assert's 
      error message is used to retrieve a message from the dictionary to show in the 
      output as the test result in case of failure.
    * *presenter* - a dictionary with any or all of the following keys: input, ref,
      res, parsed. Each key must be paired with a function that returns a string. These
      functions are used to make data structures cleaner in the output. See section
      :ref:`Presenters <presenters>` for more information.
    * *output_parser* - a function that retrieves data by parsing the student 
      program's output. Output parsers can abort the test case by raising 
      OutputParseError.
    * *message_validator* - a function that validates the student program's raw 
      output (as opposed to parsing values from it). This validation is done 
      separately from the main validator function. Like the validator, it must use
      assert, and the assert's error message is used to retrieve a message to show. 
      If omitted, message validation will not be performed. 
    * *new_test* - a function that is called at the start of each test case. Can be
      used to reset the state of persistent objects within the checker. Receives 
      arguments (as None) and inputs when called.
    
    The number of test cases is determined from the length of the test vector. Even if 
    the testing with no inputs at all, your test vector must contain an empty list
    for each test case! 
    
    Each test case is processed as follows. During the test, sys.stdout is restored
    whenever a message is shown to the student.
    
    #. new_test callback is called
    #. Stored output is cleared and output is redirected to the StringOutput object
    #. StringIO object is formed from the test vector to replace sys.stdin
    #. The student program is reloaded using :func:`importlib.reload`. 
    
       * If there is an error, the appropriate error message is retrieved from the 
         dictionary. Inputs are also shown in the output. Testing proceeds to the next 
         case.
    
    #. If hide_output is False, the student output is shown in the evaluation 
    #. The student function output is parsed
    
       * If there is an error, OutputParseError message is shown along with 
         OutputPatternInfo. Inputs are also shown in the evaluation output. Testing 
         proceeds to the next case. 
         
    #. The validator is called 
    
       * Regardless of outcome, inputs and student result are always shown.
       * If succcessful, the CorrectResult message is shown in the output.
       * If unsuccessful, the following steps are taken to provide more information
       
         #. A message explaining the problem is shown, along with the reference.
         #. False reference functions are called and validated against the student 
            result. A message corresponding to the function name is shown if
            the validation is a match.
         #. Custom test functions are called and appropriate messages are shown if
            they raise AssertionErrors.
         #. If test_recurrence is True, a message is printed if the student program
            produced the same result as the last test.
         #. Information functions are called and their corresponding messages are
            shown in the output, including the information function's return value.
             
    #. If test_messages is True, message_validator is called.
    
       * If successful, the CorrectMessage message is shown in the output.
       * If unsuccessful, a message explaining the problem is shown along with 
         the MessageInfo message and the student program's raw output.
    """


    # One time preparations
    save = sys.stdout
    msgs = load_messages(lang, "program")
    msgs.update(custom_msgs)
    
    if isinstance(presenter, dict):
        input_presenter = presenter.get("input", defaults.default_input_presenter)
        ref_presenter = presenter.get("ref", defaults.default_value_presenter)
        parsed_presenter = presenter.get("parsed", defaults.default_value_presenter)
    else:        
        input_presenter = presenter
        ref_presenter = presenter
        parsed_presenter = presenter


    if inspect.isfunction(test_vector):
        test_vector = test_vector()
    
    #output(msgs.get_msg("ProgramName", lang).format(name=st_module.__name__), INFO)
    json_output.new_test(
        msgs.get_msg("ProgramName", lang)["content"].format(name=st_module.__name__)
    )

    o = StringOutput()
    sys.stdout = o
    
    tests = []
    for v in test_vector:
        tests.append((v, ref_func(*v)))
    
    prev_out = None
    
    # Running the tests
    for inputs, ref in tests:
        json_output.new_run()
        new_test(None, inputs)
        reset_locals(st_module)
        
        # Test preparations
        sys.stdout = o
        o.clear()
            
        sys.stdin = io.StringIO("\n".join([str(x) for x in inputs]))
        
        # Running the student module
        try:
            importlib.reload(st_module)
        except:
            sys.stdout = save
            etype, evalue, etrace = sys.exc_info()
            ename = evalue.__class__.__name__
            emsg = str(evalue)
            elineno, eline = get_exception_line(st_module, etrace)
            output(msgs.get_msg(ename, lang, default="GenericErrorMsg"), Codes.ERROR,
                inputs=input_presenter(inputs),
                emsg=emsg,
                ename=ename
            )
            output(msgs.get_msg("PrintExcLine", lang), Codes.DEBUG, lineno=elineno, line=eline)
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=input_presenter(inputs))
            return 
            
        # Validating program results
        values_printed = False
        sys.stdout = save
        if not hide_output:
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)
                
        # Parse output
        try:
            st_out = output_parser(o.content)
        except OutputParseError as e:
            output(msgs.get_msg("OutputParseError", lang), Codes.INCORRECT,
                inputs=input_presenter(inputs),
                output=o.content,
                reason=str(e)
            )
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG,
                inputs=input_presenter(inputs)
            )
            output(msgs.get_msg("OutputPatternInfo", lang), Codes.INFO)
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)
            continue

        # Validation
        try: 
            validator(ref, None, st_out)
            output(msgs.get_msg("CorrectResult", lang), Codes.CORRECT)
        except AssertionError as e:
            # Result was incorrect
            output(msgs.get_msg(e, lang, "IncorrectResult"), Codes.INCORRECT)
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=input_presenter(inputs))
            output(msgs.get_msg("PrintStudentResult", lang), Codes.DEBUG,
                parsed=parsed_presenter(st_out), output=o.content
            )
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)  
            output(msgs.get_msg("PrintReference", lang), Codes.DEBUG, ref=ref_presenter(ref))
            values_printed = True
            if error_refs or custom_tests or test_recurrence:
                output(msgs.get_msg("AdditionalTests", lang), Codes.INFO)
            
            # Run false references
            for eref_func in error_refs:
                eref = eref_func(*inputs)
                try: 
                    validator(eref, None, st_out)
                    output(msgs.get_msg(eref_func.__name__, lang), Codes.INFO)
                except AssertionError as e:
                    pass
                    
            # Run custom tests
            for test in custom_tests:
                try: 
                    test(None, st_out, o.content, ref, None, inputs)
                except AssertionError as e:
                    output(msgs.get_msg(e, lang, test.__name__), Codes.INFO)
                    
            # Test for result recurrence
            if test_recurrence and st_out == prev_out:
                output(msgs.get_msg("RepeatingResult", lang), Codes.INFO)

            # Run info functions
            if info_funcs:
                output(msgs.get_msg("AdditionalInfo", lang), Codes.INFO)
                for info_func in info_funcs:
                    try:
                        output(msgs.get_msg(info_func.__name__, lang), Codes.INFO,
                            func_res=info_func(None, st_out, o.content, ref, None, inputs)
                        )
                    except NoAdditionalInfo:
                        pass
        else:
            # Result was correct
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=input_presenter(inputs))
            output(msgs.get_msg("PrintStudentResult", lang), Codes.DEBUG,
                parsed=parsed_presenter(st_out),
                output=o.content
            )
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)  
            values_printed = True

        # Validate student output
        if message_validator:
            try: 
                message_validator(o.content, None, inputs)
                output(msgs.get_msg("CorrectMessage", lang), Codes.CORRECT)
            except AssertionError as e:
                output(msgs.get_msg(e, lang, "IncorrectMessage"), Codes.INCORRECT)
                output(msgs.get_msg("MessageInfo", lang), Codes.INFO)
                if not values_printed:
                    output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)  
                    output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG,
                        inputs=input_presenter(inputs)
                    )
                
        prev_out = None
