import pandas as pd
import sys
import time
from pathlib import Path
from loguru import logger




sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from config import get_duckdb, DATABASE_PATH, SP500_CACHE_PATH


