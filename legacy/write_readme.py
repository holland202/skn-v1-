import sys, base64
data = sys.stdin.read().strip()
readme = base64.b64decode(data).decode('utf-8')
with open('README.md', 'w') as f:
    f.write(readme)
print('README.md written:', len(readme), 'bytes')
