# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['aico.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../shared', 'shared'),
        ('../config', 'config'),
    ],
    hiddenimports=[
        'typer', 
        'rich', 
        'click', 
        'shellingham', 
        'typing_extensions',
        'pkg_resources',
        'keyring',
        'cryptography',
        'cryptography.hazmat.primitives.kdf.argon2',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'libsql',
        # Configuration management dependencies
        'yaml',
        'jsonschema',
        'watchdog',
        'watchdog.observers',
        'watchdog.events',
        # Note: aico.* modules are included via datas and imported dynamically at runtime
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='aico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
