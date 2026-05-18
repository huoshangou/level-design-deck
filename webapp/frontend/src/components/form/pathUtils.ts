// dot path 解析 / get / set，与 tools/regenerate_field.parse_path 同思路。
// 支持：
//   - 普通 key: "meta.spec_id"
//   - array index: "nodes[0].label"
//   - array by-id: "nodes[entry].label"（按 item.id 字段匹配）

export type PathSeg = { kind: "key"; val: string } | { kind: "idx"; val: string };

const SEG_RE = /^([^[]+)(?:\[([^\]]+)\])?$/;

export function parsePath(path: string): PathSeg[] {
  const out: PathSeg[] = [];
  for (const raw of path.split(".")) {
    const m = SEG_RE.exec(raw);
    if (!m) throw new Error(`malformed path segment: ${raw}`);
    out.push({ kind: "key", val: m[1] });
    if (m[2] !== undefined) out.push({ kind: "idx", val: m[2] });
  }
  return out;
}

export function getByPath(root: unknown, path: string): unknown {
  let cur: unknown = root;
  for (const seg of parsePath(path)) {
    if (seg.kind === "key") {
      if (cur && typeof cur === "object" && !Array.isArray(cur) && seg.val in (cur as object)) {
        cur = (cur as Record<string, unknown>)[seg.val];
      } else {
        return undefined;
      }
    } else {
      if (!Array.isArray(cur)) return undefined;
      const asNum = Number(seg.val);
      if (Number.isInteger(asNum) && String(asNum) === seg.val) {
        cur = cur[asNum];
      } else {
        const hit = cur.find((x) => x && typeof x === "object" && (x as Record<string, unknown>).id === seg.val);
        if (hit === undefined) return undefined;
        cur = hit;
      }
    }
    if (cur === undefined) return undefined;
  }
  return cur;
}

/**
 * Immutable set: 返回新 root，原 root 不变（React-friendly）。
 * 不会创建中间不存在的路径——如果中间缺则 throw。
 */
export function setByPath<T>(root: T, path: string, value: unknown): T {
  const segs = parsePath(path);
  if (segs.length === 0) return value as T;

  function recur(node: unknown, i: number): unknown {
    const seg = segs[i];
    const isLast = i === segs.length - 1;

    if (seg.kind === "key") {
      if (node === null || typeof node !== "object" || Array.isArray(node)) {
        throw new Error(`setByPath: expected object at segment ${i} (key '${seg.val}')`);
      }
      const obj = node as Record<string, unknown>;
      const child = obj[seg.val];
      return { ...obj, [seg.val]: isLast ? value : recur(child, i + 1) };
    }

    if (!Array.isArray(node)) {
      throw new Error(`setByPath: expected array at segment ${i}`);
    }
    const asNum = Number(seg.val);
    let idx: number;
    if (Number.isInteger(asNum) && String(asNum) === seg.val) {
      idx = asNum;
    } else {
      idx = node.findIndex(
        (x) => x && typeof x === "object" && (x as Record<string, unknown>).id === seg.val
      );
      if (idx < 0) throw new Error(`setByPath: array item with id='${seg.val}' not found`);
    }
    const next = node.slice();
    next[idx] = isLast ? value : recur(node[idx], i + 1);
    return next;
  }

  return recur(root, 0) as T;
}
