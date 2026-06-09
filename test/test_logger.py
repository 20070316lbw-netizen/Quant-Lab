import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test.data.testlogger import GetSP500List
g = GetSP500List()
result = g.fetch_wiki()