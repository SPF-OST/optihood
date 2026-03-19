import warnings
import oemof
import pandas as pd

import re
from typing import Optional, Match

# Suppress FutureWarnings from oemof
warnings.filterwarnings("ignore", category=FutureWarning, module="oemof")

def pattern_at_start_followed_by_number(pattern: str, label: str) -> Optional[Match[str]]:
   return re.match(fr"^{pattern}(\d+)?$", label)

class LabelStringManipulator:
   def __init__(self, label):
      self.full_name = label
      splitted_label = label.split("__")
      self.prefix = splitted_label[0]
      self.building = splitted_label[1]

   def strip_trailing_digits_from_prefix(self):
      return self.prefix.rstrip("0123456789")


def has_valid_value(s: dict, label: str) -> bool:
   """Returns True if the label exists, is not NaN, and is not 'x' or 'X'."""
   return (
           label in s
           and pd.notna(s[label])
           and s[label] not in ('x', 'X')
   )