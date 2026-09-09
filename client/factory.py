"""Read-only factory snapshot through the fixed controller command."""
import json
from .play import call


def snapshot():
    return call('factory')


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
