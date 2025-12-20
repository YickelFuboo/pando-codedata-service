import os

def helper_function():
    return "helper"

def main_function():
    result = helper_function()
    path = os.path.join("test", "path")
    return result

