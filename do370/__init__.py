import os
import importlib
try:
    module = importlib.import_module("do370")
    __ANSIBLE_ROLES_PATH__ =\
        os.path.dirname(module.__file__) + "/ansible/roles"
except ModuleNotFoundError:
    pass
