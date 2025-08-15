# promptdbqt.spec — PyInstaller-Konfiguration (OneFile, noconsole)
# Hinweis: Icon kann über build.ps1-Parameter gesetzt werden.
# promptdbqt.spec — statische Variante (OneFile + noconsole)
from PyInstaller.utils.hooks import collect_submodules
block_cipher = None

# promptdbqt.spec — OneFile + noconsole; Icon kann per CLI überschrieben werden
from PyInstaller.utils.hooks import collect_submodules
block_cipher = None

hidden = ['PySide6.QtCore','PySide6.QtGui','PySide6.QtWidgets']
hidden += collect_submodules('PySide6')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('.env.template','.'), ('docs/*.md','docs')],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='PromptDBQt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None
)
