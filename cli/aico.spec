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
        # Core dependencies
        'typer', 'rich', 'click', 'shellingham', 'typing_extensions',
        # Package resources for namespace packages
        'pkg_resources',
        # Security and encryption
        'keyring', 'cryptography', 'cryptography.fernet', 'cryptography.hazmat',
        'cryptography.hazmat.primitives', 'cryptography.hazmat.backends',
        'cryptography.hazmat.primitives.kdf', 'cryptography.hazmat.primitives.kdf.argon2',
        'cryptography.hazmat.primitives.kdf.pbkdf2', 'cryptography.hazmat.primitives.hashes',
        # Database
        'libsql', 'sqlite3',
        # ZeroMQ for unified logging system
        'zmq', 'pyzmq',
        # AICO modules
        'aico.security', 'aico.data.libsql', 'aico.data.libsql.encrypted',
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
