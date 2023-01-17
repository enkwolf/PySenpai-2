import os.path
import pkg_resources
import sys
from enum import IntEnum
import yaml

class Codes(IntEnum):
    INCORRECT = 0
    CORRECT = 1
    INFO = 2
    ERROR = 3
    DEBUG = 4
    LINT_C = 10 #10
    LINT_R = 11 #11
    LINT_W = 12 #12
    LINT_E = 13 #13


class TranslationDict(dict):
    """
    This class is a customized dictionary that supports the multilingual support
    needed by PySenpai. Values are stored using two-part keys: keyword and
    language. Internally the keys are represented as strings in the form of
    :code:`"keyword:language"`.
    Three convenience methods are provided for storing and reading values from
    the dictionary.
    
    The core module comes with a set of predefined messages for each of test
    functions. When implementing checkers you can provide a TranslationDict
    object of your own which will be used to update the default dictionary for
    the test. See section :ref:`Output Messages <output-messages>` for more
    information.
    
    The class is usually used for output messages, but it is also handy for
    defining and retrieving regular expressions in multiple languages. 
    """   
    
    def set_msg(self, key, lang, value):
        """
        set_msg(key, lang, value)
        
        Sets a new *value* into the dictionary, forming a two-part key of *key* and *lang*.
        When using as a custom message dictionary, value can be either a string or a
        dictionary with up to three keys: content (str), hints (list) and triggers (list).
        If used internally within the checker, no limitations apply for value. However the
        update method only works with supported types of values.
        """
        
        self.__setitem__("{}:{}".format(key, lang), value)
        
    def get_msg(self, key, lang, default=None):
        """
        get_msg(key, lang[, default=None]) -> value
        
        Gets a value from the dictionary using *key* and *lang* to find the corresponding
        value. If the corresponding value is not found and *default* is set, another get 
        is performed using *default* and *lang* as the two-part key. If *default* is not 
        set or the corresponding value is not found, KeyError is raised.         
        """
        
        try:
            return self.__getitem__("{}:{}".format(key, lang))
        except KeyError:
            if default:
                return self.__getitem__("{}:{}".format(default, lang))
        raise KeyError(key)
                
    def get_many(self, lang, *keys):
        """
        get_many(lang[, key1, ...]) -> list
        
        Gets multiple values from the dictionary and returns them as a list. Each *key* is 
        paired with *lang* to form the two-part keys. If any two-part key fails to match, a
        KeyError is raised.    
        """
        
        msgs = []
        for key in keys:
            msgs.append(self.get_msg(key, lang))
        return msgs
                
    def copy(self):
        """
        copy() -> TranslationDict
        
        Returns a copy.
        """
        
        return TranslationDict(self.items())
    
    def update(self, patch):
        """
        update(patch)
        
        Updates the dictionary from another TranslationDict instance. If a key already
        exists its value is updated by a) replacing its content value with the new value
        if the new value is a string; or b) running a normal dictionary update if it's a
        dictionary.
        
        If the key doesn't exist, it is added. The value is always a dictionary - if the
        given value is a string a dictionary is created and the string is placed into the
        content field.
        """
        
        for key, value in patch.items():
            try:
                if isinstance(value, str):
                    self.__getitem__(key)["content"] = value
                elif isinstance(value, dict):
                    self.__getitem__(key).update(value)
                else:
                    raise TypeError("Message must be str or dict")
            except KeyError:
                if isinstance(value, str):
                    self.__setitem__(key, {"content": value})
                else:
                    self.__setitem__(key, value)


def load_messages(lang, category, module="pysenpai"):
    msgs = TranslationDict()
    msg_path = pkg_resources.resource_filename(module, "msg_data")
    try:
        with open(os.path.join(msg_path, lang, "messages.yml"), encoding="utf-8") as msg_file:
            msg_dict = yaml.safe_load(msg_file)
    except FileNotFoundError:
        sys.exit(f"ERROR: Messages for module {module} not found for language {lang}")
    
    for key, value in msg_dict[category].items():
        msgs.set_msg(key, lang, dict(content=value))
    return msgs
    
