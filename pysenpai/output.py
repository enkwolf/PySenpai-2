class JsonOutput(dict):
    """
    This class represents the JSON output of PySenpai. It is a dictionary with
    some added convenience methods for manipulating the inner data structures
    which would otherwise get out of hand with all the indexing and keying. It
    is only managed internally - checkers should not meddle with it. However, 
    should you really feel the need to, the internal output object can be 
    accessed as test_core.json_output.
    
    The JSON document created by this function matches the specification for
    the Lovelace learning environment's exercise evaluation format.
    """
    
    
    def __init__(self):
        super().__init__(self)
        self.__setitem__("tester", "")
        self.__setitem__("tests", [])
        
    def set_tester(self, name):
        """
        Sets the tester field of the JSON document. Usually this is called by 
        :func:`~test_core.set_tester` if you need to set it. The field is not
        currently required.
        """
        
        self.__setitem__("tester", name)
        
    def new_test(self, title):
        """
        This is called when a new test begins, i.e. when one of the test 
        functions (including load module) are called. It starts a new test
        structure in the JSON document with *title* as its title that will be
        shown in the output.
        """
        
        self.__getitem__("tests").append({
            "title": title,
            "runs": []
        })
        
    def new_run(self):
        """
        This is called when a new test case begins. There is no title, it 
        simply indicates that a new run structure should be started in the JSON
        document.
        """
        
        self.__getitem__("tests")[-1]["runs"].append({
            "output": []
        })
        
    def new_msg(self, content, flag, triggers=[], hints=[]):
        """
        Adds a new message to the test case output where *content* is the 
        actual message to be shown in the test log and *flag* is its category.
        A message can also include a list *triggers* that and *hints*. These 
        are explained in more detail under :ref:`output-messages`. 
        """
        
        self.__getitem__("tests")[-1]["runs"][-1]["output"].append({
            "msg": content,
            "flag": flag,
            "triggers": triggers,
            "hints": hints
        })
        
    def grind_params(self, template, var_names, values, question):
        """
        Adds grind parameters to the output. These are used only when the checker
        is a grind type checker and is used to generate a new task instance. 
        """
        
        self.__setitem__("grind_params", 
            {
                "template": template,
                "variables": var_names,
                "values": values, 
                "question": question
            }
        )
            
    def wrap_to(self, wrapper_dict, keyname):
        """
        Puts the evaluation dictionary inside another dictionary, using the
        specified *keyname*. The object then assumes the contents of
        *wrapper_dict* as its own. This method is used for routine type
        exercises that need to provided more context information than just the
        evaluation report.
        
        The reason this method is needed is the automatic output of the json
        report when this module exits. Therefore the output of the checker must
        always be contained in this module's internal dictionary - it cannot
        print its own output.
        """
    
        wrapper_dict[keyname] = self.copy()
        self.clear()
        self.update(wrapper_dict)


def output(msg, flag, **format_args):
    """
    Outputs message into the JSON document. Just a shorthand that makes the
    rest of the code look less messy.
    """
    
    if msg["content"]:
        json_output.new_msg(
            msg["content"].format(**format_args), 
            flag,
            msg.get("triggers", []),
            msg.get("hints", [])
        )

json_output = JsonOutput()
