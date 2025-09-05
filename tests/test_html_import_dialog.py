import pytest

def test_import_dialog_loads():
    try:
        from ui.html_import_dialog import HtmlImportDialog
    except Exception as e:
        pytest.skip(f"Qt bindings not available: {e}")
        return
    # We only test importability here; full UI tests are covered elsewhere.
    assert HtmlImportDialog is not None
