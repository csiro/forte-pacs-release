"""
Module with dicom query related enums and classes.
"""
from enum import Enum
from typing import List



class MatchType(Enum):
    """
    Enumeration of different types of attribute matches that can be used in a query.
    See https://dicom.nema.org/medical/dicom/current/output/chtml/part04/sect_C.2.2.2.html

    single_value: Match a single value.
    list_of_uid: Match a list of unique identifiers.
    universal: Match any value.
    wildcard: Match a wildcard pattern.
    range: Match a range of values.
    sequence: Match a sequence of values.
    empty: Match an empty value.
    multiple: Match multiple values.
    fuzzy: Match a fuzzy value.
    """
    single_value = 1
    list_of_uid = 2
    universal = 3
    wildcard = 4
    range = 5
    sequence = 6
    empty = 7
    multiple = 8
    fuzzy = 9

class QueryLevel(Enum):
    """
    Enumeration of different levels of a DICOM query.
    Query can be performed at the study, series, or instance level.
    """
    study = 1
    series = 2
    instance = 3


class QueryAttributeMatch:
    """
    A class representing a query component with attribute match type, level, name, and value.
        Todo:
            - convert to dataclass?

    """

    def __init__(self,match_type : MatchType, ie_level : QueryLevel, attr_name : str, value : str | List[str] | None = None):
        """
        Represents a query component with an attribute match type, level, name, and value.

        Args:
            match_type (MatchType): The type of attribute match to use.
            ie_level (QueryLevel): The level of the DICOM query (study, series, or instance).
            attr_name (str): The name of the attribute to match.
            value (str | List[str], optional): The value(s) to match against the attribute.
        """
        self.match_type=match_type
        self.level = ie_level
        self.attr_name = attr_name
        self.value = value

