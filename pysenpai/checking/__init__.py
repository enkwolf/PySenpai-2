from abc import ABC, abstractmethod
from pysenpai.callbacks.defaults import result_validator

class TestCase(ABC):
    
    def __init__(self, args, weight, ref_result, validator=result_validator, inputs=None):
        self.args = args
        self.inputs = inputs or []
        self.weight = weight
        self.ref_result = ref_result
        self.validator = validator
        self.correct = False
    
    def feedback(self, res, parsed, output):
        pass

    def parse(self, output):
        return output
    
    def validate(self, res, parsed, output):
        self.validator(res, parsed, output)
        self.correct = True
    
    @abstractmethod
    def wrap(self, callable):
        pass



