import warnings
import oemof

import re
from typing import Optional, Match

# Suppress FutureWarnings from oemof
warnings.filterwarnings("ignore", category=FutureWarning, module="oemof")

def pattern_at_start_followed_by_number(pattern: str, label: str) -> Optional[Match[str]]:
   return re.match(fr"^{pattern}(\d+)?$", label)
