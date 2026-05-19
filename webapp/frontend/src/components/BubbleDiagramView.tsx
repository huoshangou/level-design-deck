import { useEffect, useRef, useState } from "react";

// node.type → Mermaid shape
const SHAPE: Record<string, (id: string, label: string) => string> = {
  entry: (id, l) => `${id}([${l}])`,
  exit: (id, l) => `${id}([${l}])`,
  scene: (id, l) => `${id}[${l}]`,
  puzzle: (id, l) => `${id}{${l}}`,
  hub: (id, l) => `${id}((${l}))`,
  branch: (id, l) => `${id}{${l}}`,
  default: (id, l) => `${id}[${l}]`,
};

// edge.type → Mermaid arrow style
const ARROW: Record<string, string> = {
  sequential: "-->",
  optional: "-.->",
  loop: "-->",
  branch: "-->",
  default: "-->",
};

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
}

interface Props {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  onNodeClick?: (nodeId: string) => void;
}

function buildMermaid(nodes: DiagramNode[], edges: DiagramEdge[]): string {
  const phases = new Map<string, DiagramNode[]>();
  const noPhase: DiagramNode[] = [];
  for (const n of nodes) {
    if (n.phase) {
      if (!phases.has(n.phase)) phases.set(n.phase, []);
      phases.get(n.phase)!.push(n);
    } else {
      noPhase.push(n);
    }
  }

  const lines: string[] = ["flowchart LR"];
  let sg = 0;
  for (const [phase, pnodes] of phases) {
    lines.push(`  subgraph sg${sg}["${phase}"]`);
    for (const n of pnodes) {
      const shapeFn = SHAPE[n.type ?? "default"] ?? SHAPE.default;
      lines.push(`    ${shapeFn(n.id, (n.label ?? n.id).replace(/"/g, "'"))}`);
    }
    lines.push("  end");
    sg++;
  }
  for (const n of noPhase) {
    const shapeFn = SHAPE[n.type ?? "default"] ?? SHAPE.default;
    lines.push(`  ${shapeFn(n.id, (n.label ?? n.id).replace(/"/g, "'"))}`);
  }
  for (const e of edges) {
    const arrow = ARROW[e.type ?? "default"] ?? ARROW.default;
    if (e.label) {
      lines.push(`  ${e.from} ${arrow}|"${e.label.replace(/"/g, "'")}"| ${e.to}`);
    } else {
      lines.push(`  ${e.from} ${arrow} ${e.to}`);
    }
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
