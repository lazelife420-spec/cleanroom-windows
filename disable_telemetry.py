#!/usr/bin/env python3
import sys

from enable_telemetry import main

if __name__ == '__main__':
    rc = main(enable=False)
    sys.exit(rc)
