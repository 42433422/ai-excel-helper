#!/usr/bin/env python3
"""为旧版 mod_store_routes 注入 aux_employee_store（生产增量部署用）。"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("/opt/fhd-full/app/fastapi_routes/mod_store_routes.py")


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if "aux_employee_store" in text:
        print("already patched")
        return

    combined_old = "    return available, list(installed_map.values())"
    combined_new = """    from app.mod_sdk.aux_employee_store import inject_aux_employee_pack_rows
    inject_aux_employee_pack_rows(available, set(installed_map.keys()))
    return available, list(installed_map.values())"""
    if combined_old not in text:
        raise SystemExit("patch anchor missing: _combined_rows return")
    text = text.replace(combined_old, combined_new, 1)

    install_marker = "async def _install_from_catalog(pkg_id: str, version: str, activate: bool = True) -> ModStoreInstallResult:\n"
    install_block = (
        install_marker
        + """    from app.mod_sdk.aux_employee_store import (
        install_aux_employee_pack_from_repo_seed,
        is_aux_employee_pack_mod_id,
    )
    if is_aux_employee_pack_mod_id(pkg_id):
        ok, message = install_aux_employee_pack_from_repo_seed(pkg_id, activate=activate)
        if ok:
            return ModStoreInstallResult(success=True, message=message, data={"id": pkg_id})

"""
    )
    if install_marker not in text:
        raise SystemExit("patch anchor missing: _install_from_catalog")
    text = text.replace(install_marker, install_block, 1)

    TARGET.write_text(text, encoding="utf-8")
    print("patched ok")


if __name__ == "__main__":
    main()
