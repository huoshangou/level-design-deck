async function openFullDocument() {
  const lid = (SPEC.meta && SPEC.meta.level_id) || '';
  if (!lid) return toast('当前 spec 无 level_id');
  toast('生成完整文档中...');
  const r = await fetch('/api/render-level?level_id=' + encodeURIComponent(lid), {method:'POST'});
  if (!r.ok) return toast('生成失败');
  window.open('/' + (await r.json()).output, '_blank'); toast('✓ 已打开');
}
