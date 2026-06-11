import pandas as pd
import sys
import time
from pathlib import Path
from loguru import logger

from config import get_duckdb, DATABASE_PATH, SP500_CACHE_PATH


