import builtins

import cmdop.exceptions
if not hasattr(cmdop.exceptions, 'TimeoutError'):
    cmdop.exceptions.TimeoutError = builtins.TimeoutError

import sys
sys.argv = ['openclaw', 'gateway', '--port', '18789', '--allow-unconfigured', '--auth', 'none']

import os
os.environ['ANTHROPIC_BASE_URL'] = 'http://127.0.0.1:5002/v1'
os.environ['ANTHROPIC_API_KEY'] = 'sk-fake-key-not-needed'

from cmdop.cli import main
main()
