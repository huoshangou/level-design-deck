import { useEffect, useRef, useState } from "react";

// 与 tools/render.py:spec_to_mermaid / NODE_SHAPE / EDGE_ARROW 同步
// node.type → Mermaid shape brackets [left, right]；label 必须双引号包裹防特殊字符炸
const NODE_SHAPE: Record<string, [string, string]> = {
  entry:    ["([", "])"],
  exit:     ["([", "])"],
  combat:   ["[", "]"],
  scene:    ["[", "]"],
  puzzle:   ["{", "}"],
  choice:   ["{", "}"],
  dialogue: ["[/", "/]"],
  cutscene: ["[\\", "\\]"],
};
const DEFAULT_SHAPE: [string, string] = ["[", "]"];

// edge.type → Mermaid arrow style
const ARROW: Record<string, string> = {
  sequential: "-->",
  branch: "-->",
  optional: "-.->",
  loop: "==>",
  failure: "-.->",
};
const DEFAULT_ARROW = "-->";

export interface DiagramNode {
  id: string;
  type?: string;
  label?: string;
  notes?: string;
  phase?: string;
}

export interface DiagramEdge {
  from: string;
  to: string;
  type?: string;
  label?: string;
  requires?: string[];
}

interface Props {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  onNodeClick?: (nodeId: string) => void;
}

function nodeDecl(n: DiagramNode): string {
  const [l, r] = NODE_SHAPE[n.type ?? ""] ?? DEFAULT_SHAPE;
  const label = (n.label ?? n.id).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  return `${n.id}${l}"${label}"${r}`;
}

function buildMermaid(nodes: DiagramNode[], edges: DiagramEdge[]): string {
  const lines: string[] = ["graph TD"];

  // M3.6: 任一节点有 phase 即启用 subgraph 分组（与 tools/render.py 一致）
  const hasAnyPhase = nodes.some((n) => !!n.phase);

  if (hasAnyPhase) {
    const order: string[] = [];
    const groups = new Map<string, DiagramNode[]>();
    for (const n of nodes) {
      const ph = n.phase ?? "";
      if (!groups.has(ph)) { groups.set(ph, []); order.push(ph); }
      groups.get(ph)!.push(n);
    }
    for (const ph of order) {
      const list = groups.get(ph)!;
      if (ph === "") {
        for (const n of list) lines.push(`  ${nodeDecl(n)}`);
      } else {
        const slug = (ph.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")) || "x";
        lines.push(`  subgraph phase_${slug}["${ph.replace(/"/g, '\\"')}"]`);
        for (const n of list) lines.push(`    ${nodeDecl(n)}`);
        lines.push("  end");
      }
    }
  } else {
    for (const n of nodes) lines.push(`  ${nodeDecl(n)}`);
  }

  for (const e of edges) {
    const et = e.type ?? "sequential";
    const arrow = ARROW[et] ?? DEFAULT_ARROW;
    const lbl = (e.label ?? "").replace(/"/g, '\\"');
    // M3.5: requires 合取前置依赖 → label 前缀 [需 X+Y]
    const reqs = e.requires ?? [];
    const prefix = reqs.length ? `[需 ${reqs.join("+")}] ` : "";
    let edgePart: string;
    if (et === "failure" && lbl) edgePart = `${arrow}|"${prefix}${lbl} (失败)"|`;
    else if (et === "failure")   edgePart = `${arrow}|"${prefix}失败"|`;
    else if (prefix || lbl)      edgePart = `${arrow}|"${prefix}${lbl}"|`;
    else                          edgePart = arrow;
    lines.push(`  ${e.from} ${edgePart} ${e.to}`);
  }
  return lines.join("\n");
}

let mermaidReady: Promise<void> | null = null;
function loadMermaid(): Promise<void> {
  if (mermaidReady) return mermaidReady;
  mermaidReady = new Promise((resolve, reject) => {
    if ((window as unknown as Record<string, unknown>).mermaid) { resolve(); return; }
    const s = document.createElement("script");
    s.src = "/lib/mermaid.min.js";
    s.onload = () => resolve();
    s.onerror = reject;
    document.head.appendChild(s);
  });
  return mermaidReady;
}

let renderSeq = 0;

// highlight color for selected node fill
const SELECTED_FILL = "#bfdbfe"; // blue-200
const SELECTED_STROKE = "#2563eb"; // blue-600

export default function BubbleDiagramView({ nodes, edges, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [err, setErr] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<DiagramNode | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  // keep ref to g elements for re-applying highlight without re-render
  const gMapRef = useRef(new Map<string, SVGGElement>());

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const definition = buildMermaid(nodes, edges);
    const id = `mermaid-${++renderSeq}`;
    gMapRef.current.clear();
    setSelectedId(null);

    loadMermaid().then(async () => {
      try {
        const m = (window as unknown as {
          mermaid: {
            initialize: (c: object) => void;
            render: (id: string, def: string) => Promise<{ svg: string }>;
          };
        }).mermaid;
        m.initialize({ startOnLoad: false, theme: "base", themeVariables: { fontSize: "13px" } });
        const { svg } = await m.render(id, definition);
        el.innerHTML = svg;
        setErr(null);

        const svgEl = el.querySelector("svg");
        if (!svgEl) return;
        svgEl.style.maxWidth = "100%";
        svgEl.style.height = "auto";

        const nodeMap = new Map(nodes.map((n) => [n.id, n]));

        svgEl.querySelectorAll<SVGGElement>(".node").forEach((g) => {
          const nid = g.getAttribute("data-id") ?? "";
          const info = nodeMap.get(nid);
          if (!info) return;
          gMapRef.current.set(nid, g);
          g.style.cursor = "pointer";

          // hover
          g.addEventListener("mouseenter", (ev) => {
            const rect = svgEl.getBoundingClientRect();
            const me = ev as MouseEvent;
            setTooltipPos({ x: me.clientX - rect.left, y: me.clientY - rect.top - 8 });
            setHoveredNode(info);
          });
          g.addEventListener("mouseleave", () => setHoveredNode(null));
          g.addEventListener("mousemove", (ev) => {
            const rect = svgEl.getBoundingClientRect();
            const me = ev as MouseEvent;
            setTooltipPos({ x: me.clientX - rect.left, y: me.clientY - rect.top - 8 });
          });

          // click → 选中 + 通知外部
          g.addEventListener("click", () => {
            setSelectedId(nid);
            onNodeClick?.(nid);
          });
        });
      } catch (e) {
        setErr(String(e));
      }
    }).catch((e) => setErr(`Mermaid 脚本加载失败: ${e}`));
  }, [nodes, edges]);

  // 选中状态变化时更新 SVG 节点的填色
  useEffect(() => {
    gMapRef.current.forEach((g, nid) => {
      const shape = g.querySelector<SVGElement>("rect, circle, polygon, ellipse");
      if (!shape) return;
      if (nid === selectedId) {
        shape.style.fill = SELECTED_FILL;
        shape.style.stroke = SELECTED_STROKE;
        shape.style.strokeWidth = "2px";
      } else {
        shape.style.fill = "";
        shape.style.stroke = "";
        shape.style.strokeWidth = "";
      }
    });
  }, [selectedId]);

  if (!nodes.length) {
    return (
      <div style={{ padding: 24, color: "var(--text-faint)", fontSize: 13 }}>
        bubble_diagram 暂无节点数据
      </div>
    );
  }

  return (
    <div style={{ position: "relative", padding: "12px 16px", overflow: "auto" }}>
      {err && (
        <pre style={{ color: "var(--error)", fontSize: 11, whiteSpace: "pre-wrap", marginBottom: 8 }}>
          Mermaid 渲染失败：{err}
        </pre>
      )}
      {onNodeClick && (
        <p style={{ margin: "0 0 6px", fontSize: 11, color: "var(--text-dim)" }}>
          点击节点跳转到对应编辑区
        </p>
      )}
      <div ref={containerRef} />
      {hoveredNode && (
        <div
          style={{
            position: "absolute",
            left: tooltipPos.x + 12,
            top: tooltipPos.y,
            maxWidth: 260,
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "8px 10px",
            fontSize: 11,
            lineHeight: 1.5,
            boxShadow: "0 4px 12px rgba(0,0,0,0.12)",
            pointerEvents: "none",
            zIndex: 50,
          }}
        >
          <strong style={{ display: "block", marginBottom: 4 }}>{hoveredNode.label ?? hoveredNode.id}</strong>
          {hoveredNode.notes && <span style={{ color: "var(--text-dim)" }}>{hoveredNode.notes}</span>}
          {onNodeClick && !hoveredNode.notes && (
            <span style={{ color: "var(--text-faint)", fontStyle: "italic" }}>点击跳转到编辑区</span>
          )}
        </div>
      )}
    </div>
  );
}
