/** 构建时由 Vite 注入（Dockerfile / CI 传入 VITE_APP_VERSION）；本地未设置则为 dev */
export const APP_VERSION = (() => {
  const v = import.meta.env.VITE_APP_VERSION;
  if (typeof v === "string" && v.trim()) return v.trim();
  return "dev";
})();
