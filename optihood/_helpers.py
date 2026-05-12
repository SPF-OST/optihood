import warnings
import oemof
import pandas as pd

# Suppress FutureWarnings from oemof
warnings.filterwarnings("ignore", category=FutureWarning, module="oemof")

def has_valid_value(s: dict, label: str) -> bool:
   """Returns True if the label exists, is not NaN, and is not 'x' or 'X'."""
   return (
           label in s
           and pd.notna(s[label])
           and s[label] not in ('x', 'X')
   )
