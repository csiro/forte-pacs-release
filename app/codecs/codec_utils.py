"""
This module contains utility functions used by codecs.

"""

from typing import Dict

def get_param(arg_dict:Dict[str,str], param_name:str)->str:
    """
        Get parameter from dictionary

        Args:
            arg_dict (Dict[str,str]): Dictionary of arguments.
            param_name (str) : name of param needed

        Returns:
            str : Value of parametr.

        Raise:
            Exception : if parameter is not present
        Notes:
            - 
    """
    temp = arg_dict.get(param_name)
    if temp is None:
        raise Exception(f"Required param {param_name} missing")
    
    return temp
