import warnings
import oemof
import pandas as pd

import re
from typing import Optional, Match

# Suppress FutureWarnings from oemof
warnings.filterwarnings("ignore", category=FutureWarning, module="oemof")


def pattern_at_start_followed_by_number(pattern: str, label: str) -> Optional[Match[str]]:
    """ TODO: this function should be replaced with LabelStringManipulator.component_name"""
    return re.match(fr"^{pattern}(\d+)?$", label)


_LABEL_SEPARATOR = "__"


class LabelStringManipulator:
    def __init__(self, label):
        self.full_name = label
        splitted_label = label.split(_LABEL_SEPARATOR)
        self.prefix = splitted_label[0]
        self.building = splitted_label[1]

    def strip_trailing_digits_from_prefix(self):
        return self.prefix.rstrip("0123456789")

    @property
    def component_name(self):
        return self.strip_trailing_digits_from_prefix()


def create_label_string(component_label: str, building_nr: str | float) -> LabelStringManipulator:
    if "Building" in building_nr:
        building_label = building_nr
    else:
        building_label = "Building" + str(int(building_nr))
    label = component_label + _LABEL_SEPARATOR + str(building_label)
    return LabelStringManipulator(label)


def has_valid_value(s: dict, label: str) -> bool:
    """Returns True if the label exists, is not NaN, and is not 'x' or 'X'."""
    return (
            label in s
            and pd.notna(s[label])
            and s[label] not in ('x', 'X')
    )
