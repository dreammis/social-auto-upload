import sys
import os
import glob

_root = os.path.dirname(__file__)

# Ensure the project root is on sys.path so test modules can import sau_backend
sys.path.insert(0, _root)

# If running under system Python with a broken Flask editable install,
# inject the local .venv's site-packages so Flask can be imported.
_venv_site = glob.glob(os.path.join(_root, ".venv", "lib", "python*", "site-packages"))
for _sp in _venv_site:
    if _sp not in sys.path:
        sys.path.insert(1, _sp)
