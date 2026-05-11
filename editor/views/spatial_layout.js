function isSpatialLayout(spec) {
  return ((spec && spec.meta && spec.meta.spec_id) || '').startsWith('spatial_layout_');
}

function renderSpatialLayoutView(spec, schema) {
  const layout = spec.layout || {};
  const layers = layout.layers || [];
  const shapes = layout.shapes || [];
  const entities = layout.entities || [];
  const labelCov = shapes.filter(s => s.label && !/^[\d.\-]+$/.test(s.label.trim())).length;
  const renderUrl = '/outputs/' + escapeHtml(spec.meta.spec_id) + '.html';
  return `
<fieldset><legend>meta</legend>${renderObject(spec.meta, schema.properties.meta, 'meta')}</fieldset>
<fieldset><legend>context</legend>${renderObject(spec.context, schema.properties.context, 'context')}</fieldset>
<fieldset>
  <legend>layout (read-only · LevelCraft 编辑)</legend>
  <details style="margin-bottom:12px">
    <summary style="cursor:pointer;font-size:12px;color:#444;font-weight:600">📖 如何编辑 layout（首次使用必看）</summary>
    <div style="font-size:11px;line-height:1.7;color:#555;margin-top:10px;padding:10px;background:#f8f8f5;border-left:3px solid #888">
      <b>① 打开 LevelCraft 编辑器</b>：点下方 [🛠 Open LevelCraft] 按钮，新标签打开。<br>
      <b>② 在 LevelCraft 中操作</b>：拖拽房间、加门窗、给区域上传参考图。如果是修改现有关卡，先点下方 [⬇ Download Current JSON] 下载当前 layout，再在 LevelCraft 里用导入功能加载它；如果是首次新建，直接从空白画布开始。<br>
      <b>③ 导出并导回</b>：在 LevelCraft 点 "Export JSON" 下载文件 → 回到这里点 [📥 Import JSON] 选刚下载的文件 → spec 自动替换 layout、保存、重新校验、重新渲染。
    </div>
  </details>
  <div style="font-size:12px;color:#666;margin-bottom:10px">⚙️ Layout 不在 deck 内编辑，只显示统计 + 校验告警</div>
  <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;font-size:11px;line-height:1.6;margin-bottom:14px">
    <div><b>name</b>: ${escapeHtml(layout.name || '?')}</div>
    <div><b>gridSize</b>: ${layout.gridSize || '?'}</div>
    <div><b>layers</b>: ${layers.length}</div>
    <div><b>shapes</b>: ${shapes.length}</div>
    <div><b>entities</b>: ${entities.length}</div>
    <div><b>label coverage</b>: ${labelCov}/${shapes.length}</div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <button type="button" onclick="window.open('/tools/levelcraft/editor.html','_blank')" style="background:#444;color:#fff;padding:8px 14px;border:none;cursor:pointer">🛠 Open LevelCraft Editor</button>
    <label style="background:#1a73e8;color:#fff;padding:8px 14px;cursor:pointer">
      📥 Import JSON
      <input type="file" accept="application/json,.json" style="display:none" onchange="importLayoutJson(this.files[0])">
    </label>
    <button type="button" onclick="downloadCurrentLayoutJson()" style="background:#fff;color:#444;padding:8px 14px;border:1px solid #ccc;cursor:pointer">⬇ Download Current JSON</button>
    <button type="button" onclick="window.open('${renderUrl}','_blank')" style="background:#fff;color:#444;padding:8px 14px;border:1px solid #ccc;cursor:pointer">🖼 Open Rendered HTML →</button>
  </div>
</fieldset>`;
}

async function importLayoutJson(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async () => {
    let parsed;
    try { parsed = JSON.parse(reader.result); }
    catch (e) { toast('JSON 解析失败: ' + e.message); return; }
    if (!parsed || !Array.isArray(parsed.shapes) || !Array.isArray(parsed.layers)) {
      toast('不是 LevelCraft JSON（缺 shapes 或 layers）'); return;
    }
    const oldN = (SPEC.layout && SPEC.layout.shapes) ? SPEC.layout.shapes.length : 0;
    if (!confirm(`即将替换 spec.layout（当前 ${oldN} shapes → 新 ${parsed.shapes.length} shapes）。继续？`)) return;
    SPEC.layout = parsed;
    await saveSpec();
    await reloadAll();
    await renderHtml();
    renderForm();
    toast('✓ Layout 已替换、保存、重新校验、重新渲染');
  };
  reader.readAsText(file);
}

function downloadCurrentLayoutJson() {
  const blob = new Blob([JSON.stringify(SPEC.layout || {}, null, 2)], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (SPEC.meta && SPEC.meta.spec_id ? SPEC.meta.spec_id : 'layout') + '_layout.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
