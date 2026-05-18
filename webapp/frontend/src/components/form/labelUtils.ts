// JSON Schema 的 title 字段做"人话主显示"，path key 做灰小字辅助。
// 与 editor.html L237 附近 labelFor / fieldLabelHtml helper 同语义。

export type SchemaLike = {
  title?: string;
  description?: string;
  [k: string]: unknown;
};

export function lastKey(path: string): string {
  const idx = path.lastIndexOf(".");
  const tail = idx >= 0 ? path.slice(idx + 1) : path;
  return tail.replace(/\[[^\]]*\]/g, "");
}

export function fieldLabel(schema: SchemaLike, path: string): { main: string; key: string } {
  const key = lastKey(path) || "(root)";
  return { main: schema.title?.trim() || key, key };
}
