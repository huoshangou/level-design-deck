"""
_cross_check_helpers.py — cross_check.py 的共享工具函数（私有模块）。

提取自 cross_check.py（M4.1+，因主文件触 300 行硬限）。
仅供 tools/cross_check.py import；不导出"规则元数据"——
什么 module 做 zone ref 的决策属于主文件领域。

标准库 only。
"""

def get_spatial_labels(spatial: dict) -> set:
    """从 spatial_layout spec 提取所有非空 shape label 集合。"""
    labels = set()
    for s in spatial.get("layout", {}).get("shapes", []):
        if isinstance(s, dict):
            label = (s.get("label") or "").strip()
            if label:
                labels.add(label)
    return labels


def check_zone_field(v, spatial_labels, items, field_path_prefix, id_key):
    """通用 zone ref 校验：遍历 items，取 id_key，不在 spatial_labels 则报 ERROR。

    Args:
        v: CrossValidator 实例（duck-typed，需有 add_error(path, rule, msg) 方法）
        spatial_labels: set，由 get_spatial_labels() 产
        items: list of dict
        field_path_prefix: str，如 "lighting_req.ambience_refs"
        id_key: str，如 "region_id"
    """
    sample = sorted(spatial_labels)[:10]
    tail = "..." if len(spatial_labels) > 10 else ""
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        zid = (item.get(id_key) or "").strip()
        if not zid:
            continue
        if zid not in spatial_labels:
            v.add_error(
                f"{field_path_prefix}[{i}].{id_key}",
                "cross_ref_integrity",
                f"{id_key} {zid!r} not in spatial_layout.shapes[].label "
                f"(available labels: {sample}{tail})",
            )


def make_zone_ref_check(module: str, collection: str, id_key: str):
    """工厂：返回一个 cross_check 函数，自动从 specs_by_module 找 module + spatial_layout
    跑通用 zone ref 校验。

    返回的函数签名：fn(specs_by_module, v)
    """
    def fn(specs_by_module, v):
        spec = specs_by_module.get(module)
        spatial = specs_by_module.get("spatial_layout")
        if not spec or not spatial:
            return
        check_zone_field(
            v, get_spatial_labels(spatial),
            spec.get(collection, []),
            f"{module}.{collection}", id_key,
        )
    return fn
