#!/bin/bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip setuptools wheel
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade -r requirements.txt
