// 按 schema 类型分发到具体子组件。
// 递归从 ObjectField / ArrayField 反向引入也走这里。

import type { SchemaLike } from "./labelUtils";
import ArrayField from "./ArrayField";
import ObjectField from "./ObjectField";
import StringField from "./StringField";
import { BoolField, NumberField } from "./NumberBoolField";

type Schema = SchemaLike & { type?: string; enum?: string[] };

type Props = {
  schema: Schema;
  value: unknown;
  path: string;
  onChange: (path: string, value: unknown) => void;
  registerRef: (path: string, el: HTMLElement | null) => void;
};

export default function Field(props: Props) {
  const { schema } = props;
  if (schema.type === "object") return <ObjectField {...props} />;
  if (schema.type === "array") return <ArrayField {...props} />;
  if (schema.type === "number" || schema.type === "integer") return <NumberField {...props} />;
  if (schema.type === "boolean") return <BoolField {...props} />;
  // 默认 string / enum / 未知 type 都走 StringField
  return <StringField {...props} />;
}
