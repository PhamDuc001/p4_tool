import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if "P4" not in sys.modules:
    stub = types.ModuleType("P4")

    class _StubP4:
        def connect(self):
            return None

        def disconnect(self):
            return None

    class _StubP4Exception(Exception):
        pass

    stub.P4 = _StubP4
    stub.P4Exception = _StubP4Exception
    sys.modules["P4"] = stub
