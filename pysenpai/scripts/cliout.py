import json
import sys

def read_lines():
    lines = sys.stdin.read().split("\n")
    for line in lines:
        try:
            log = json.loads(line)
        except json.JSONDecodeError as e:
            print(e)
        else:
            break
    
    return log

def print_log(log):
    for test in log["tests"]:
        print(test["title"])
        for i, run in enumerate(test["runs"], start=1):
            print()
            print("---- run {} ----".format(i))
            for output in run["output"]:
                print(output["msg"])
                
def main():
    log = read_lines()
    print_log(log)