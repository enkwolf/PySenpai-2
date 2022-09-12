class OutputParseError(Exception):
    """
    This exception should be raised by :ref:`output parsers <output-parsers>` if
    they fail to parse the student code's output properly.  This exception is
    handled in :func:`~test_core.test_function` and will result in:
    
    * the parsed result set to None
    * output of OutputParseError message with INCORRECT flag
    * output of OutputPatternInfo message with INFO flag    

    When raising *reason* can be given as additional information provided about
    the problem. The reason string is available as a keyword argument for format
    specifiers inside the OutputParseError message.
    """
    
    msg = ""

    def __init__(self, reason=""):
        super().__init__(self)
        self.msg = reason
        
    def __str__(self):
        return self.msg


class NoAdditionalInfo(Exception):
    """
    This exception should be raised by 
    :ref:`additional information functions <info-functions>` if they come to the
    conclusion that there is in fact no additional information that they can 
    give. It prevents the info function's message from being shown in the output. 
    """
    
    pass

class NoMatchingObject(Exception):
    """
    Raised by :func:`~test_core.find_objects` when it's unable to find objects
    of the specified type.
    """
    
    pass

class NotCallable(Exception):
    
    def __init__(self, name):
        super().__init__(self)
        self.callable_name = name
        