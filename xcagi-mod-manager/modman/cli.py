from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modman import __version__
from modman.manifest_util import patch_manifest_fields, read_manifest, validate_manifest_dict
from modman.scaffold import create_mod
from modman.store import (
    default_library,
    default_xcagi_root,
    deploy_to_xcagi,
    export_zip,
    import_zip,
    ingest_mod,
    list_mods,
    pull_from_xcagi,
)


def _library_path(ns: argparse.Namespace) -> Path:
    return Path(ns.library).expanduser().resolve() if ns.library else default_library()


def cmd_list(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    rows = list_mods(lib)
    if ns.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print(f"(库为空) {lib}")
        return 0
    for r in rows:
        st = "OK" if r.get("ok") else "!!"
        print(f"[{st}] {r.get('id')}  v{r.get('version', '')}  {r.get('name', '')}")
        if r.get("warnings"):
            for w in r["warnings"]:
                print(f"      · {w}")
        if r.get("error"):
            print(f"      · {r['error']}")
    print(f"\n库根目录: {lib}")
    return 0


def cmd_validate(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    targets: list[Path] = []
    if ns.path:
        targets.append(Path(ns.path).expanduser().resolve())
    else:
        targets = [Path(r["path"]) for r in list_mods(lib) if r.get("path")]
    bad = 0
    for p in targets:
        if not p.is_dir():
            print(f"跳过（非目录）: {p}")
            bad += 1
            continue
        data, err = read_manifest(p)
        if err:
            print(f"{p.name}: {err}")
            bad += 1
            continue
        ve = validate_manifest_dict(data)
        from modman.manifest_util import folder_name_must_match_id

        fn = folder_name_must_match_id(p, data)
        if fn:
            ve.append(fn)
        if ve:
            print(f"{p.name}:")
            for v in ve:
                print(f"  · {v}")
            bad += 1
        else:
            print(f"{p.name}: 校验通过")
    return 1 if bad else 0


def cmd_ingest(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    dest = ingest_mod(Path(ns.src), lib)
    print(f"已入库: {dest}")
    return 0


def cmd_new(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    dest = create_mod(ns.mod_id, ns.name, lib)
    print(f"已创建脚手架: {dest}")
    print("下一步: 编辑代码后 modman validate，再 modman push 部署到 XCAGI。")
    return 0


def cmd_push(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    xcagi = Path(ns.xcagi).expanduser().resolve() if ns.xcagi else default_xcagi_root()
    if not xcagi or not xcagi.is_dir():
        print("未找到 XCAGI 根目录。请设置环境变量 XCAGI_ROOT 或传入 --xcagi", file=sys.stderr)
        return 1
    ids = [x.strip() for x in ns.mods.split(",") if x.strip()] if ns.mods else None
    done = deploy_to_xcagi(ids, lib, xcagi, replace=not ns.no_replace)
    print(f"已部署到 {xcagi / 'mods'}: {', '.join(done) or '(无)'}")
    return 0


def cmd_pull(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    xcagi = Path(ns.xcagi).expanduser().resolve() if ns.xcagi else default_xcagi_root()
    if not xcagi or not xcagi.is_dir():
        print("未找到 XCAGI 根目录。请设置 XCAGI_ROOT 或 --xcagi", file=sys.stderr)
        return 1
    ids = [x.strip() for x in ns.mods.split(",") if x.strip()] if ns.mods else None
    done = pull_from_xcagi(ids, lib, xcagi, replace=not ns.no_replace)
    print(f"已从 XCAGI 拉回库: {', '.join(done) or '(无)'}")
    return 0


def cmd_export(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    mod_dir = lib / ns.mod_id
    if not mod_dir.is_dir():
        print(f"库中无此 Mod: {mod_dir}", file=sys.stderr)
        return 1
    export_zip(mod_dir, Path(ns.zip_path).expanduser().resolve())
    print(f"已导出: {ns.zip_path}")
    return 0


def cmd_import_zip(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    dest = import_zip(Path(ns.zip).expanduser().resolve(), lib, replace=not ns.no_replace)
    print(f"已导入: {dest}")
    return 0


def cmd_set_meta(ns: argparse.Namespace) -> int:
    lib = _library_path(ns)
    mod_dir = lib / ns.mod_id
    if not mod_dir.is_dir():
        print(f"库中无此 Mod: {mod_dir}", file=sys.stderr)
        return 1
    updates = {}
    if ns.name is not None:
        updates["name"] = ns.name
    if ns.version is not None:
        updates["version"] = ns.version
    if ns.author is not None:
        updates["author"] = ns.author
    if ns.description is not None:
        updates["description"] = ns.description
    if ns.primary is not None:
        updates["primary"] = ns.primary
    if not updates:
        print("请至少指定 --name / --version / --author / --description / --primary", file=sys.stderr)
        return 1
    patch_manifest_fields(mod_dir, updates)
    print(f"已更新 manifest: {mod_dir / 'manifest.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="modman",
        description="XCAGI Mod 库：集中存放、校验、与 XCAGI/mods 同步。",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    lib_arg = argparse.ArgumentParser(add_help=False)
    lib_arg.add_argument(
        "--library",
        "-L",
        help="库根目录（默认: 本项目 library/ 或环境变量 MODMAN_LIBRARY）",
    )

    sp = sub.add_parser("list", parents=[lib_arg], help="列出库中所有 Mod")
    sp.set_defaults(func=cmd_list)
    sp.add_argument("--json", action="store_true", help="JSON 输出")

    sp = sub.add_parser("validate", parents=[lib_arg], help="校验 manifest（可指定路径或扫描整个库）")
    sp.set_defaults(func=cmd_validate)
    sp.add_argument("path", nargs="?", help="单个 Mod 目录；省略则校验库内全部")

    sp = sub.add_parser("ingest", parents=[lib_arg], help="从任意目录拷贝入库（按 manifest.id 命名目标文件夹）")
    sp.set_defaults(func=cmd_ingest)
    sp.add_argument("src", help="含 manifest.json 的 Mod 源码目录")

    sp = sub.add_parser("new", parents=[lib_arg], help="从模板新建 Mod 脚手架")
    sp.set_defaults(func=cmd_new)
    sp.add_argument("mod_id", help="Mod 目录名与 manifest.id，如 acme-labels")
    sp.add_argument("--name", "-n", required=True, help="显示名称")

    sp = sub.add_parser("push", parents=[lib_arg], help="将库中 Mod 部署到 XCAGI/mods")
    sp.set_defaults(func=cmd_push)
    sp.add_argument("--xcagi", help="XCAGI 项目根目录（默认: 环境变量 XCAGI_ROOT 或 ../XCAGI）")
    sp.add_argument(
        "--mods",
        help="仅部署这些 id，逗号分隔；省略表示库内全部通过校验的 Mod",
    )
    sp.add_argument(
        "--no-replace",
        action="store_true",
        help="目标已存在则报错（默认覆盖）",
    )

    sp = sub.add_parser("pull", parents=[lib_arg], help="从 XCAGI/mods 拉回库（备份/归集）")
    sp.set_defaults(func=cmd_pull)
    sp.add_argument("--xcagi", help="XCAGI 项目根目录")
    sp.add_argument("--mods", help="仅拉取指定 id，逗号分隔；省略表示全部")
    sp.add_argument("--no-replace", action="store_true")

    sp = sub.add_parser("export", parents=[lib_arg], help="将库中某个 Mod 打成 zip")
    sp.set_defaults(func=cmd_export)
    sp.add_argument("mod_id")
    sp.add_argument("zip_path", help="输出 .zip 路径")

    sp = sub.add_parser("import-zip", parents=[lib_arg], help="从 zip 导入到库（顶层单文件夹）")
    sp.set_defaults(func=cmd_import_zip)
    sp.add_argument("zip")
    sp.add_argument("--no-replace", action="store_true")

    sp = sub.add_parser("set-meta", parents=[lib_arg], help="修改库中 Mod 的 manifest 常用字段")
    sp.set_defaults(func=cmd_set_meta)
    sp.add_argument("mod_id")
    sp.add_argument("--name")
    sp.add_argument("--version")
    sp.add_argument("--author")
    sp.add_argument("--description")
    sp.add_argument("--primary", type=lambda x: str(x).lower() in {"1", "true", "yes"})

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    try:
        return int(ns.func(ns))
    except (ValueError, FileNotFoundError, FileExistsError) as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
