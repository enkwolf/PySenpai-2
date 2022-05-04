import importlib
import inspect
import io
import sys

import pysenpai.callbacks.defaults as defaults
import pysenpai.callbacks.convenience as convenience
from pysenpai.output import json_output
from pysenpai.messages import load_messages, Codes
from pysenpai.output import output
from pysenpai.utils.internal import StringOutput, get_exception_line, reset_locals

# NOTE: custom_msgs, inputs, error_refs, custom_tests, info_funcs are read only
# therefore setting defaults to empty lists / dictionaries is safe here. 
def test_code_snippet(st_code, constructor, ref_func, 
                      lang="en",
                      custom_msgs={},
                      inputs=[],
                      hide_output=True,
                      error_refs=[],
                      custom_tests=[],
                      info_funcs=[],
                      validator=convenience.vars_validator,
                      presenter=defaults.default_presenters,
                      output_parser=defaults.default_parser,
                      message_validator=None):
    """
    test_code_snippet(st_code, constructor, ref_func[, lang="en"][, kwarg1][, ...])
    
    Tests a code snippet. The snippet can be put into a larger context by using
    a *constructor* function. The snippet along with its context is written into
    a temporary module and run. After running the namespace of the module is
    evaluated against a reference object provided by the reference function.
    
    * *st_code* - a string that contains the code snippet
    * *constructor* - a function that creates a full program around the snippet.
      This can include setting initial values for variables etc.
    * *ref_func* - reference function that is given the input vector as arguments
      and should return an object that can be compared with the student
      submission's namespace. It should **not** consume inputs (i.e. don't call
      :func:`input`).
    * *lang* - language for messages
    * *custom_msgs* - a TranslationDict object that includes additions/overrides 
      to the default code snippet test messages
    * *hide_output* - a flag to show/hide student program prints in the test 
      output. By default student output is hidden. 
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
      vars, parsed. Each key must be paired with a function that returns a string. These
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
    
    Currently code snippet tests only run once. They proceed as follows:
    
    #. Real stdout is saved, messages are updated from custom messages given by
       the checker and presenters are set. Inputs are written into a StringIO 
       and stdin is pointed there.
    #. The reference result is obtained from the reference function.
    #. Student submission is constructed into a temporary module using the constructor.
       The module is written into a file.
    #. The code is executed by importing the temporary module. 

       * If there is an error, the appropriate error message is retrieved from the 
         dictionary. Inputs are also shown in the output. Testing is aborted.
    
    #. Output is printed unless *hide_output* is True.
    #. The output is parsed for values.

       * If there is an error, OutputParseError message is shown along with 
         OutputPatternInfo. Inputs are also shown in the evaluation output. Testing 
         is aborted.
         
    #. The validator is run, comparing the namespaces of the temporary modules against
       a reference object, or parsed values against the reference (or both). 
       
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
    """
    
    
    # One time preparations
    correct = True
    
    save = sys.stdout
    msgs = load_messages(lang, "snippet")
    msgs.update(custom_msgs)
    
    if isinstance(presenter, dict):
        input_presenter = presenter.get("input", defaults.default_input_presenter)
        ref_presenter = presenter.get("ref_vars", defaults.default_vars_presenter)
        parsed_presenter = presenter.get("parsed", defaults.default_value_presenter)
        vars_presenter = presenter.get("vars", defaults.default_vars_presenter)
        code_presenter = presenter.get("code", defaults.default_construct_presenter)
    else:        
        input_presenter = presenter
        ref_presenter = presenter
        parsed_presenter = presenter
        vars_presenter = presenter
        code_presenter = presenter
        
    json_output.new_test(msgs.get_msg("SnippetTest", lang)["content"])
    
    o = StringOutput()
    sys.stdout = o
    
    json_output.new_run()
    
    sys.stdout = o
    o.clear()
        
    sys.stdin = io.StringIO("\n".join([str(x) for x in inputs]))
    
    ref = ref_func(inputs)
    
    # Construct the module and write it to a file
    full_code = constructor(st_code)
    with open("temp_module.py", "w") as target:
        target.write(full_code)
        
    if full_code != st_code:
        output(msgs.get_msg("PrintConstructedCode", lang), Codes.INFO, code=code_presenter(full_code))
    
    # Load the module and obtain output
    try:
        temp_module = importlib.import_module("temp_module")
    except:
        sys.stdout = save
        etype, evalue, etrace = sys.exc_info()
        ename = evalue.__class__.__name__
        emsg = str(evalue)
        output(msgs.get_msg(ename, lang, default="GenericErrorMsg"), Codes.ERROR,
            ename=ename,
            emsg=emsg,
            inputs=input_presenter(inputs)
        )
        if inputs:
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=presenter(inputs))
        return False

    # Resume output to normal stdout and show output if not hidden
    values_printed = False
    sys.stdout = save
    if not hide_output:
        output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)

    # Parse the output into a result
    try:
        st_out = output_parser(o.content)
    except OutputParseError as e:
        output(msgs.get_msg("OutputParseError", lang), Codes.INCORRECT,
            inputs=input_presenter(inputs),
            output=o.content,
            reason=str(e)
        )
        output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=input_presenter(inputs))
        output(msgs.get_msg("OutputPatternInfo", lang), Codes.INFO)
        output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)
        return False

    # Validate the result
    try:
        validator(ref, temp_module, st_out)
        output(msgs.get_msg("CorrectResult", lang), Codes.CORRECT)
    except AssertionError as e:
        # Result was incorrect
        correct = False
        output(msgs.get_msg(e, lang, "IncorrectResult"), Codes.INCORRECT)
        if inputs:
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG,
                inputs=presenter(inputs)
            )
        output(msgs.get_msg("PrintStudentResult", lang), Codes.DEBUG,
            res=vars_presenter(temp_module),
            parsed=st_out,
            output=o.content
        )
        if o.content:
            output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)
        output(msgs.get_msg("PrintReference", lang), Codes.DEBUG, ref=ref_presenter(ref))
        value_printed = True
        if error_refs or custom_tests:
            output(msgs.get_msg("AdditionalTests", lang), Codes.INFO)

        # Run validation against false references
        for eref_func in error_refs:
            eref = eref_func(inputs)
            try: 
                validator(ref, temp_module, st_out)
                output(msgs.get_msg(eref_func.__name__, lang), Codes.INFO)
            except AssertionError as e:
                pass

        # Run custom tests
        for test in custom_tests:
            try: 
                test(temp_module, st_out, o.content, ref, None, inputs)
            except AssertionError as e:
                output(msgs.get_msg(e, lang, test.__name__), Codes.INFO)

        # Run info functions
        if info_funcs:
            output(msgs.get_msg("AdditionalInfo", lang), Codes.INFO)
            for info_func in info_funcs:
                try:
                    output(msgs.get_msg(info_func.__name__, lang), Codes.INFO, 
                        func_res=info_func(temp_module, st_out, o.content, ref, None, inputs)
                    )
                except NoAdditionalInfo:
                    pass
    else:
        # Result was correct
        if inputs:
            output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=input_presenter(inputs))
        output(msgs.get_msg("PrintStudentResult", lang), Codes.DEBUG,
            res=vars_presenter(temp_module),
            parsed=st_out,
            output=o.content
        )
        values_printed = True

    # Validate output messages
    if message_validator:
        try: 
            message_validator(o.content, None, inputs)
            output(msgs.get_msg("CorrectMessage", lang), Codes.CORRECT)
        except AssertionError as e:
            correct = False
            output(msgs.get_msg(e, lang, "IncorrectMessage"), Codes.INCORRECT)
            output(msgs.get_msg("MessageInfo", lang), Codes.INFO)
            if not values_printed:
                output(msgs.get_msg("PrintStudentOutput", lang), Codes.INFO, output=o.content)  
                output(msgs.get_msg("PrintInputVector", lang), Codes.DEBUG, inputs=input_presenter(inputs))

    return correct
