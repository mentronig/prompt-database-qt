
import pytest

# Prefer PySide6, fallback to PyQt5
try:
    from PySide6.QtWidgets import QApplication, QMainWindow
    qt_api = "PySide6"
except Exception:
    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow
        qt_api = "PyQt5"
    except Exception:
        QApplication = None
        QMainWindow = object  # dummy
        qt_api = None


def _make_window():
    if qt_api is None:
        pytest.skip("Qt (PySide6/PyQt5) not installed; skipping UI test.")
    from ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    # Support both signatures: MainWindow(app) and MainWindow()
    try:
        win = MainWindow(app)
    except TypeError:
        win = MainWindow()
    return app, win, MainWindow


@pytest.mark.ui
def test_main_window_class_exists_and_is_qmainwindow():
    if qt_api is None:
        pytest.skip("Qt (PySide6/PyQt5) not installed; skipping UI test.")
    from ui.main_window import MainWindow
    assert issubclass(MainWindow, QMainWindow)


@pytest.mark.ui
def test_main_window_instantiation_show_and_close():
    app, win, MainWindow = _make_window()
    win.show()
    app.processEvents()
    assert isinstance(win, MainWindow)
    title = win.windowTitle() if hasattr(win, "windowTitle") else ""
    assert isinstance(title, str)
    win.close()
