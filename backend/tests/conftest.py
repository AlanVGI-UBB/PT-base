import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "modelo: prueba de humo que carga el modelo real de faster-whisper",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    markexpr = config.getoption("-m", default="") or ""
    if "modelo" in markexpr:
        return
    skip_modelo = pytest.mark.skip(
        reason="prueba con modelo real; ejecutar con: pytest backend/tests -m modelo"
    )
    for item in items:
        if "modelo" in item.keywords:
            item.add_marker(skip_modelo)
