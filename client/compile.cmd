@echo off
uv run python versionfile.py
uv run pyinstaller --clean --noconfirm --windowed --upx-dir=C:\upx --name vcgc --version-file=vdata.txt client.py