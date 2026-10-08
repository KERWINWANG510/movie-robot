/** 规范化相对挂载根路径（去首尾斜杠、统一分隔符） */
export function normalizeRelPath(p: string): string {
  return p.replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
}

export function breadcrumbPartsOf(path: string): string[] {
  const n = normalizeRelPath(path);
  if (!n) return [];
  return n.split("/").filter(Boolean);
}

export function parentRelPath(path: string): string {
  const parts = breadcrumbPartsOf(path);
  parts.pop();
  return parts.join("/");
}
