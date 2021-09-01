python3 -m venv .venv
source .venv/bin/activate

python -m pip install -i https://pypi.doubanio.com/simple --upgrade pip setuptools wheel
pip install -i https://pypi.doubanio.com/simple -r requirements_linux.txt
