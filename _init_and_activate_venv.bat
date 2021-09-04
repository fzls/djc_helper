python -m venv .venv
call .venv\Scripts\activate.bat

python -m pip install -i https://pypi.doubanio.com/simple --upgrade pip setuptools wheel
pip install -i https://pypi.doubanio.com/simple --upgrade -r requirements.txt
