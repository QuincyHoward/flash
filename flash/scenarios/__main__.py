# -*- coding: utf-8 -*-
"""python -m flash.scenarios —— 统一入口（转发 core.cli）"""
import sys

from flash.scenarios.core.cli import main

sys.exit(int(main(sys.argv[1:]) or 0))
