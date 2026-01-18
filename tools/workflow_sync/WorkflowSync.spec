# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Workflow Sync Tool.

Genera un ejecutable standalone para macOS.
Uso: pyinstaller WorkflowSync.spec
"""

import sys
from pathlib import Path

# Directorio base
block_cipher = None
base_path = Path(SPECPATH)

a = Analysis(
    ['interactive.py'],
    pathex=[str(base_path)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'github',
        'github.MainClass',
        'github.GithubException',
        'github.Repository',
        'github.ContentFile',
        'github.PullRequest',
        'github.Branch',
        'github.GitRef',
        'urllib3',
        'requests',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WorkflowSync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Aplicación de terminal
    disable_windowed_traceback=False,
    argv_emulation=True,  # Para macOS - permite arrastrar archivos
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

