import warnings
import oemof

# Suppress FutureWarnings from oemof
warnings.filterwarnings("ignore", category=FutureWarning, module="oemof")

warnings.filterwarnings(action='ignore', category=UserWarning, message=r"Boolean Series.*")
