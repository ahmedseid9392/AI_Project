import os, glob
root = r'c:\Users\Admin\Documents\AMD\newAI\student_performance_system\.venv\Lib\site-packages\django\templatetags'
for path in glob.glob(os.path.join(root, '*.py')):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    if 'json_script' in text:
        print(path)
