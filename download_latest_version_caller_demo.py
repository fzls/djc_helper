import subprocess

py_path = ".\\.venv_dev\\Scripts\\python.exe"
script_path = ".\\download_latest_version.py"

cmd = [py_path, script_path]
output = subprocess.check_output(cmd).decode('utf-8').strip()
print(output)

boundary_mark = "$$boundary$$"

# temp = output.split(boundary_mark)
# for idx, item in enumerate(temp):
#     print(f"\t{idx}: {item}")

result = output.split(boundary_mark)[1].strip()
print(result)
