"""
This module includes core functionality for implementing tasks where individual questions are
generated from given parameters. It also includes tools to chain these questions together to form
a task that is scored based on how many individual questions have been answered correctly


"""

import random
import string
import pysenpai.callbacks.defaults as defaults
from pysenpai.callbacks.convenience import vars_validator
from pysenpai.checking.testcase import FunctionTestCase, ProgramTestCase



RANDOM = 0
SERIAL = 1


class CommonBase:

    QUESTION_CLASS = -1

    def construct_module(self, answer, params):
        return answer

    @property
    def extra_messages(self):
        return {}

    @property
    def cases(self):
        raise NotImplementedError

    @classmethod
    def _params_dict(cls, raw, formatdict=None, meta=None):
        return {
            "raw": raw,
            "formatdict": formatdict or raw,
            "meta": meta or {},
            "question_class": cls.QUESTION_CLASS
        }


class ProgramBase(CommonBase, ProgramTestCase):

    def __init__(self, params):
        super().__init__(
            ref_result=self._make_reference(params),
            validator=vars_validator,
            presenters={
                "res": defaults.default_vars_presenter,
                "ref": defaults.default_vars_presenter,
            }
        )

    @property
    def cases(self):
        return [self]

    def wrap(self, st_module, target):
        super().wrap(st_module, target)
        return st_module


class FunctionBase(CommonBase, FunctionTestCase):

    def __init__(self, params):
        super().__init__(
            ref_result=self._make_reference(params),
        )

    @property
    def cases(self):
        return [self]

    def _make_reference(self, params):
        raise NotImplementedError





def basic_scoring(stats, done, remaining):
    return int(remaining <= 0), remaining <= 0

def process_results(questions, history, max_score, active, target, lang,
                    scoring_function=basic_scoring,
                    mode=RANDOM):
    '''
    Determines what and if a question needs to be asked.
    - Depends on cmd line argument and the amount of correct questions answered.
    '''

    choices = []
    stats = {}
    remaining = 0
    done = 0
    extra_correct = 0
    for qc in active:
        correct = history.count([qc, True])
        incorrect = history.count([qc, False])
        done += correct
        if correct < target:
            choices.append(qc)
            remaining += target - correct
        else:
            extra_correct += correct - target

        stats[qc] = (target, correct, incorrect)

    score, completed = scoring_function(stats, done, remaining)
    if completed:
        choices = active

    if mode == RANDOM:
        next_q = questions[random.choice(choices)].generate(lang)
    elif mode == SERIAL:
        next_q = questions[len([record for record in history if record[1]]) % len(active)].generate(lang)

    return {
        "correct": bool(history) and history[-1][1],
        "question_class": history and history[-1][0],
        "score": score,
        "max": max_score,
        "completed": completed,
        "progress": f"{done} / {done + remaining - extra_correct}",
        "next": next_q
    }


def write_module(constructed_code, name="temp_module.py"):
    with open(name, "w", encoding="utf-8") as f:
        f.write(constructed_code)









