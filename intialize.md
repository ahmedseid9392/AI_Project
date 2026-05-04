✅ Create a Python venv and install packages
1. Open terminal in your workspace
In VS Code, open a terminal in AI_Project.

2. Create the virtual environment
Run:python -m venv .venv

3. Activate the virtual environment
run  .venv\Scripts\Activate.ps1

4. Install packages
With the venv active, install packages using pip:
pip install package_name
e.g pip install django

5. Install from requirements.txt
If you have a requirements.txt file:
pip install -r requirements.txt

6. Verify installation
pip list