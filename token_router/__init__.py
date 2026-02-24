"""TokenRouter - Multi-Model AI Token Optimization Service."""

import os
import sys

# Add SSH_WEB root to path for nlp/ and services/ imports
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)
