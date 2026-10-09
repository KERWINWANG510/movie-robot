import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { breadcrumbPartsOf, normalizeRelPath } from "../utils/path";

const FILE_ROUTE_NAMES = new Set(["rename", "folder-merge", "transfer"]);

/**
 * 文件页当前目录与 URL ?path= 同步，并在本地记住，跨重命名/合并/传输共用。
 */
export function useBrowsePath() {
  const route = useRoute();
  const router = useRouter();
  const prefs = useBrowsePrefsStore();

  const currentPath = computed(() => {
    const q = route.query.path;
    if (typeof q === "string") return normalizeRelPath(q);
    return "";
  });

  const breadcrumbParts = computed(() => breadcrumbPartsOf(currentPath.value));

  function setPath(next: string, replace = true) {
    if (!FILE_ROUTE_NAMES.has(String(route.name))) return;
    const n = normalizeRelPath(next);
    prefs.setSavedBrowsePath(n);
    const query: Record<string, string | string[]> = { ...route.query } as Record<
      string,
      string | string[]
    >;
    if (n) query.path = n;
    else delete query.path;

    const target = { name: route.name as string, query };
    if (replace) void router.replace(target);
    else void router.push(target);
  }

  /** 进入文件页且 URL 无 path 时，从本地恢复 */
  function hydrateFromStorage() {
    if (!FILE_ROUTE_NAMES.has(String(route.name))) return;
    if (typeof route.query.path === "string") {
      prefs.setSavedBrowsePath(normalizeRelPath(route.query.path));
      return;
    }
    const saved = normalizeRelPath(prefs.getSavedBrowsePath());
    if (saved) setPath(saved, true);
  }

  watch(
    () => route.query.path,
    (q) => {
      if (typeof q === "string") prefs.setSavedBrowsePath(normalizeRelPath(q));
      else if (q === undefined && FILE_ROUTE_NAMES.has(String(route.name))) {
        /* 无 path 表示根，同步本地 */
        prefs.setSavedBrowsePath("");
      }
    },
  );

  return { currentPath, breadcrumbParts, setPath, hydrateFromStorage };
}

/** 在文件管理子页之间跳转时保留 path 查询参数 */
export function fileRouteLocation(name: "rename" | "folder-merge" | "transfer", path?: string) {
  const prefs = useBrowsePrefsStore();
  const p = normalizeRelPath(path ?? prefs.getSavedBrowsePath());
  return p ? { name, query: { path: p } } : { name };
}
