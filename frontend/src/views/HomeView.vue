<script setup lang="ts">
import {
  CopyDocument,
  Document,
  Folder,
  HomeFilled,
  MagicStick,
  Picture,
  Refresh,
  Setting,
  Top,
  VideoCamera,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type TableInstance } from "element-plus";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import http from "../api/http";
import DirPickerDialog from "../components/DirPickerDialog.vue";
import OpResultDialog, { type OpResultItem } from "../components/OpResultDialog.vue";
import SetupChecklist from "../components/SetupChecklist.vue";
import TransferPanel from "../components/TransferPanel.vue";
import { fileRouteLocation, useBrowsePath } from "../composables/useBrowsePath";
import { useAuthStore } from "../stores/auth";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { errMsg } from "../utils/errMsg";
import { formatBytes } from "../utils/formatBytes";
import { parentRelPath } from "../utils/path";

type FileMode = "rename" | "folder-merge" | "transfer";

type FileEntry = { name: string; path: string; is_dir: boolean; size?: number | null };

type BrowseResponse = {
  path: string;
  entries: FileEntry[];
};

type PreviewRow = {
  path: string;
  original_name: string;
  suggested_name: string;
  error: string | null;
};

type PreviewResponse = {
  preview_id: string | null;
  items: PreviewRow[];
};

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const prefs = useBrowsePrefsStore();
const { currentPath, breadcrumbParts, setPath, hydrateFromStorage } = useBrowsePath();

const mountReady = ref(false);
const setupLoading = ref(true);

const entries = ref<FileEntry[]>([]);
const browseLoading = ref(false);
const nameFilter = ref("");
const typeFilter = ref<"all" | "file" | "dir">("all");

const selectedPaths = ref<string[]>([]);
const tableRef = ref<TableInstance>();
const transferPanelRef = ref<InstanceType<typeof TransferPanel> | null>(null);

const fileMode = computed<FileMode>(() => {
  if (route.name === "folder-merge") return "folder-merge";
  if (route.name === "transfer") return "transfer";
  return "rename";
});
const mergeMode = computed(() => fileMode.value === "folder-merge");
const transferMode = computed(() => fileMode.value === "transfer");
const renameMode = computed(() => fileMode.value === "rename");

const mergeTargetPath = ref("");
const mergeLoading = ref(false);
const dirPickerOpen = ref(false);

function onFileModeTab(name: string | number) {
  const mode = String(name) as FileMode;
  if (mode === fileMode.value) return;
  router.push(fileRouteLocation(mode));
}

const previewRows = ref<PreviewRow[]>([]);
const previewId = ref<string | null>(null);
const previewLoading = ref(false);
const executeLoading = ref(false);
const batchPrefix = ref("");
const batchSuffix = ref("");

const resultOpen = ref(false);
const resultTitle = ref("操作结果");
const resultItems = ref<OpResultItem[]>([]);
const resultCanRetry = ref(false);
let pendingRetryKind: "rename" | "merge" | null = null;
let pendingRetryPayload: unknown = null;

const filteredEntries = computed(() => {
  const q = nameFilter.value.trim().toLowerCase();
  return entries.value.filter((e) => {
    if (prefs.hideDotfiles && e.name.startsWith(".")) return false;
    if (typeFilter.value === "file" && e.is_dir) return false;
    if (typeFilter.value === "dir" && !e.is_dir) return false;
    if (q && !e.name.toLowerCase().includes(q)) return false;
    return true;
  });
});

async function refreshMountAndBrowse(resetPath = false) {
  setupLoading.value = true;
  try {
    const { data } = await http.get<{ mount_ready: boolean }>("/settings");
    mountReady.value = data.mount_ready;
    if (resetPath) setPath("");
    if (data.mount_ready) {
      hydrateFromStorage();
      await loadBrowse();
      mergeTargetPath.value = currentPath.value;
    } else {
      entries.value = [];
      selectedPaths.value = [];
      previewRows.value = [];
      previewId.value = null;
    }
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
    mountReady.value = false;
  } finally {
    setupLoading.value = false;
  }
}

async function syncMountAndCurrentBrowse() {
  setupLoading.value = true;
  try {
    const { data } = await http.get<{ mount_ready: boolean }>("/settings");
    mountReady.value = data.mount_ready;
    if (!data.mount_ready) {
      entries.value = [];
      selectedPaths.value = [];
      previewRows.value = [];
      previewId.value = null;
    } else {
      hydrateFromStorage();
      await loadBrowse();
    }
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
    mountReady.value = false;
  } finally {
    setupLoading.value = false;
  }
}

const FILE_MODES = new Set(["rename", "folder-merge", "transfer"]);

/** 按当前模式裁剪勾选，不重载目录列表 */
async function pruneSelectionForMode() {
  const keep = new Set(
    entries.value.filter((e) => selectedPaths.value.includes(e.path) && selectable(e)).map((e) => e.path),
  );
  selectedPaths.value = [...keep];
  await nextTick();
  const table = tableRef.value;
  if (!table) return;
  table.clearSelection();
  for (const row of filteredEntries.value) {
    if (keep.has(row.path)) table.toggleRowSelection(row, true);
  }
}

watch(
  () => route.name,
  async (name, oldName) => {
    if (name !== "rename" && name !== "folder-merge" && name !== "transfer") return;

    if (oldName === undefined) {
      await refreshMountAndBrowse(false);
      return;
    }

    // 三模式之间切换：复用同一目录区，不重新拉取列表
    if (FILE_MODES.has(String(oldName))) {
      if (name === "folder-merge") {
        previewRows.value = [];
        previewId.value = null;
        mergeTargetPath.value = currentPath.value;
      } else if (name === "transfer") {
        previewRows.value = [];
        previewId.value = null;
      }
      await pruneSelectionForMode();
      if (name === "transfer") {
        await nextTick();
        void transferPanelRef.value?.reloadDestinations();
      }
      return;
    }

    await syncMountAndCurrentBrowse();
    if (name === "transfer") {
      await nextTick();
      void transferPanelRef.value?.reloadDestinations();
    }
  },
  { immediate: true },
);

function selectable(row: FileEntry) {
  if (transferMode.value) return true;
  return mergeMode.value ? row.is_dir : !row.is_dir;
}

async function loadBrowse() {
  if (!mountReady.value) return;
  browseLoading.value = true;
  try {
    const { data } = await http.get<BrowseResponse>("/files/browse", {
      params: { path: currentPath.value },
    });
    entries.value = data.entries;
    selectedPaths.value = [];
    await nextTick();
    tableRef.value?.clearSelection();
  } catch (e: unknown) {
    const msg = errMsg(e);
    ElMessage.error(msg);
    if (msg.includes("不存在")) setPath("");
  } finally {
    browseLoading.value = false;
  }
}

function enterDir(row: FileEntry) {
  if (!row.is_dir) return;
  setPath(row.path);
}

function onRowDblClick(row: FileEntry) {
  enterDir(row);
}

function goRoot() {
  setPath("");
}

function goIndex(idx: number) {
  setPath(breadcrumbParts.value.slice(0, idx + 1).join("/"));
}

function goParent() {
  if (!currentPath.value) return;
  setPath(parentRelPath(currentPath.value));
}

function onSelectionChange(rows: FileEntry[]) {
  if (transferMode.value) {
    selectedPaths.value = rows.map((r) => r.path);
  } else if (mergeMode.value) {
    selectedPaths.value = rows.filter((r) => r.is_dir).map((r) => r.path);
  } else {
    selectedPaths.value = rows.filter((r) => !r.is_dir).map((r) => r.path);
  }
}

function selectAllOfType(kind: "file" | "dir" | "visible") {
  const table = tableRef.value;
  if (!table) return;
  table.clearSelection();
  for (const row of filteredEntries.value) {
    if (kind === "visible") {
      table.toggleRowSelection(row, true);
      continue;
    }
    if (kind === "dir" ? row.is_dir : !row.is_dir) {
      if (selectable(row)) table.toggleRowSelection(row, true);
    }
  }
}

async function onTransferDone() {
  selectedPaths.value = [];
  await loadBrowse();
}

function useCurrentDirAsMergeTarget() {
  mergeTargetPath.value = currentPath.value;
}

function onDirPicked(path: string) {
  mergeTargetPath.value = path;
}

function showResults(title: string, items: OpResultItem[], canRetry: boolean) {
  resultTitle.value = title;
  resultItems.value = items;
  resultCanRetry.value = canRetry;
  resultOpen.value = true;
}

async function runMerge(pathsOverride?: string[]) {
  const sources = pathsOverride ?? selectedPaths.value;
  if (sources.length < 2) {
    ElMessage.warning("请至少勾选两个要合并的文件夹");
    return;
  }
  try {
    await ElMessageBox.confirm(
      "将把所选各文件夹内（含子文件夹）的全部文件移动到目标目录下，同名文件会自动加 _1、_2 等后缀；合并完成后会删除已清空的原文件夹。此操作会移动真实文件，是否继续？",
      "文件夹合并",
      { type: "warning", confirmButtonText: "合并", cancelButtonText: "取消" },
    );
  } catch {
    return;
  }
  mergeLoading.value = true;
  try {
    const { data } = await http.post<{
      results: { source_path: string; dest_path: string; ok: boolean; message: string | null }[];
      moved_count: number;
      failed_count: number;
    }>("/files/folders/merge", {
      source_paths: sources,
      target_path: mergeTargetPath.value.trim(),
    });
    const items: OpResultItem[] = data.results.map((r, i) => ({
      key: `${r.source_path}-${i}`,
      source: r.source_path,
      dest: r.dest_path,
      ok: r.ok,
      message: r.message,
    }));
    if (data.failed_count === 0) {
      ElMessage.success(`已合并 ${data.moved_count} 个文件`);
    } else {
      ElMessage.warning(`完成：成功 ${data.moved_count}，失败 ${data.failed_count}`);
    }
    pendingRetryKind = "merge";
    pendingRetryPayload = {
      source_paths: sources,
      target_path: mergeTargetPath.value.trim(),
    };
    showResults("文件夹合并结果", items, data.failed_count > 0);
    selectedPaths.value = [];
    previewRows.value = [];
    previewId.value = null;
    await loadBrowse();
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    mergeLoading.value = false;
  }
}

async function runPreview() {
  if (selectedPaths.value.length === 0) {
    ElMessage.warning("请先勾选要重命名的文件");
    return;
  }
  previewLoading.value = true;
  previewId.value = null;
  try {
    const { data } = await http.post<PreviewResponse>("/rename/preview", {
      paths: selectedPaths.value,
    });
    previewRows.value = data.items.map((r) => ({ ...r }));
    previewId.value = data.preview_id;
    const ok = data.items.filter((x) => !x.error).length;
    ElMessage.success(`预览完成：${ok}/${data.items.length} 条生成建议`);
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    previewLoading.value = false;
  }
}

const canExecute = computed(() => {
  const rows = previewRows.value.filter((r) => !r.error);
  if (rows.length === 0) return false;
  return rows.every((r) => r.suggested_name.trim().length > 0);
});

async function runExecute(itemsOverride?: { path: string; new_name: string }[]) {
  const auto = auth.user?.auto_rename_without_preview ?? false;
  let items = itemsOverride;
  if (!items) {
    if (!canExecute.value) {
      ElMessage.warning("请完善预览结果中的新文件名");
      return;
    }
    if (!auto && !previewId.value) {
      ElMessage.warning("请先完成预览，或开启全自动模式");
      return;
    }
    items = previewRows.value
      .filter((r) => !r.error)
      .map((r) => ({ path: r.path, new_name: r.suggested_name.trim() }));
  }

  executeLoading.value = true;
  try {
    const { data } = await http.post<{ results: { path: string; ok: boolean; message: string | null }[] }>(
      "/rename/execute",
      {
        preview_id: auto || itemsOverride ? null : previewId.value,
        items,
      },
    );
    const failed = data.results.filter((x) => !x.ok);
    const itemsUi: OpResultItem[] = data.results.map((r, i) => ({
      key: `${r.path}-${i}`,
      source: r.path,
      ok: r.ok,
      message: r.message,
    }));
    if (failed.length === 0) ElMessage.success("重命名完成");
    else ElMessage.warning(`部分失败：${failed.length} 项`);
    pendingRetryKind = "rename";
    pendingRetryPayload = items
      .filter((it) => failed.some((f) => f.path === it.path))
      .map((it) => ({ ...it }));
    showResults("重命名结果", itemsUi, failed.length > 0);
    if (failed.length === 0) {
      previewRows.value = [];
      previewId.value = null;
    } else {
      previewRows.value = previewRows.value.filter((r) => failed.some((f) => f.path === r.path));
      previewId.value = null;
    }
    await loadBrowse();
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    executeLoading.value = false;
  }
}

async function runAutoPipeline() {
  await runPreview();
  await nextTick();
  if (!canExecute.value) return;
  await runExecute();
}

function applyBatchNames() {
  const pre = batchPrefix.value;
  const suf = batchSuffix.value;
  if (!pre && !suf) {
    ElMessage.warning("请填写前缀或后缀");
    return;
  }
  for (const row of previewRows.value) {
    if (row.error) continue;
    const name = row.suggested_name.trim();
    const dot = name.lastIndexOf(".");
    if (dot > 0) {
      const base = name.slice(0, dot);
      const ext = name.slice(dot);
      row.suggested_name = `${pre}${base}${suf}${ext}`;
    } else {
      row.suggested_name = `${pre}${name}${suf}`;
    }
  }
  ElMessage.success("已应用到建议名");
}

async function onResultRetry(failed: OpResultItem[]) {
  resultOpen.value = false;
  if (pendingRetryKind === "rename" && Array.isArray(pendingRetryPayload)) {
    const map = new Map(
      (pendingRetryPayload as { path: string; new_name: string }[]).map((x) => [x.path, x]),
    );
    const items = failed.map((f) => map.get(f.source)).filter(Boolean) as {
      path: string;
      new_name: string;
    }[];
    if (items.length) await runExecute(items);
    return;
  }
  if (pendingRetryKind === "merge" && pendingRetryPayload && typeof pendingRetryPayload === "object") {
    const payload = pendingRetryPayload as { source_paths: string[]; target_path: string };
    mergeTargetPath.value = payload.target_path;
    if (payload.source_paths.length >= 2) await runMerge(payload.source_paths);
    else ElMessage.warning("无法重试，请重新勾选文件夹后再合并");
  }
}

function goSettings() {
  prefs.setReturnTo(route.fullPath);
  router.push({ name: "settings-storage" });
}

async function createFolder() {
  let name: string;
  try {
    const { value } = await ElMessageBox.prompt("请输入文件夹名称", "新建文件夹", {
      confirmButtonText: "创建",
      cancelButtonText: "取消",
      inputPlaceholder: "例如：新剧集",
      inputPattern: /^[^\\/:*?"<>|]+$/,
      inputErrorMessage: '名称不能包含 \\ / : * ? " < > |',
      inputValidator: (v) => {
        const s = (v ?? "").trim();
        if (!s) return "名称不能为空";
        if (s === "." || s === "..") return "名称无效";
        if (s.endsWith(".") || s.endsWith(" ")) return "名称不能以空格或点结尾";
        return true;
      },
    });
    name = String(value ?? "").trim();
  } catch {
    return;
  }
  try {
    await http.post<{ path: string; name: string }>("/files/folders", {
      parent_path: currentPath.value,
      name,
    });
    ElMessage.success(`已创建「${name}」`);
    await loadBrowse();
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  }
}

watch(currentPath, () => {
  if (mountReady.value) void loadBrowse();
});

function onKeydown(ev: KeyboardEvent) {
  const tag = (ev.target as HTMLElement | null)?.tagName;
  const inField = tag === "INPUT" || tag === "TEXTAREA" || (ev.target as HTMLElement)?.isContentEditable;
  if (ev.key === "Backspace" && !inField && !ev.metaKey && !ev.ctrlKey) {
    if (currentPath.value) {
      ev.preventDefault();
      goParent();
    }
    return;
  }
  if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") {
    if (transferMode.value) {
      void transferPanelRef.value?.runTransfer();
    } else if (mergeMode.value) {
      if (selectedPaths.value.length >= 2) void runMerge();
    } else if (previewRows.value.length && canExecute.value) {
      void runExecute();
    } else if (selectedPaths.value.length) {
      void runPreview();
    }
  }
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => window.removeEventListener("keydown", onKeydown));

const pageTitle = computed(() => {
  if (transferMode.value) return "文件传输";
  if (mergeMode.value) return "文件夹合并";
  return "文件重命名";
});

const pageDesc =
  "统一浏览已挂载存储目录，快捷切换重命名、文件夹合并与文件传输工作流。";

const checklistContext = computed(() => {
  if (transferMode.value) return "transfer" as const;
  if (mergeMode.value) return "merge" as const;
  return "rename" as const;
});

const typeCounts = computed(() => {
  const list = entries.value.filter((e) => !(prefs.hideDotfiles && e.name.startsWith(".")));
  const dirs = list.filter((e) => e.is_dir).length;
  const files = list.length - dirs;
  return { all: list.length, file: files, dir: dirs };
});

const selectedEntries = computed(() =>
  entries.value.filter((e) => selectedPaths.value.includes(e.path)),
);

const selectedBytes = computed(() =>
  selectedEntries.value.reduce((sum, e) => sum + (e.is_dir ? 0 : Number(e.size) || 0), 0),
);

const selectionSummary = computed(() => {
  const n = selectedPaths.value.length;
  if (!n) return "未选择项目";
  if (renameMode.value) {
    return `已选择 ${n} 个媒体文件（共计 ${formatBytes(selectedBytes.value)}）`;
  }
  if (mergeMode.value) return `已选择 ${n} 个文件夹`;
  return `已选择 ${n} 项`;
});

const displayPathParts = computed(() => breadcrumbParts.value);

async function copyCurrentPath() {
  const text = currentPath.value || "/";
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制路径");
  } catch {
    ElMessage.error("复制失败");
  }
}

function entryKind(row: FileEntry): "dir" | "video" | "image" | "doc" {
  if (row.is_dir) return "dir";
  const lower = row.name.toLowerCase();
  if (/\.(mkv|mp4|avi|mov|ts|m2ts|wmv|flv|webm)$/.test(lower)) return "video";
  if (/\.(jpg|jpeg|png|gif|webp|bmp|svg)$/.test(lower)) return "image";
  return "doc";
}

function statusBadge(row: FileEntry): { text: string; tone: "dir" | "pending" | "asset" | "meta" } {
  if (row.is_dir) return { text: "目录卷", tone: "dir" };
  const kind = entryKind(row);
  if (kind === "video") return { text: "待匹配", tone: "pending" };
  if (kind === "image") return { text: "资源附件", tone: "asset" };
  return { text: "元数据文档", tone: "meta" };
}
</script>

<template>
  <div class="home-page" v-loading="setupLoading">
    <template v-if="mountReady">
      <div class="page-head">
        <div class="page-head-text">
          <h1 class="page-title">
            <span>文件管理</span>
            <span class="title-badge">UNIFIED WORKSPACE</span>
          </h1>
          <p class="page-desc">{{ pageDesc }}</p>
        </div>
        <div class="mode-seg" role="tablist">
          <button
            type="button"
            class="mode-seg-btn"
            :class="{ active: renameMode }"
            role="tab"
            :aria-selected="renameMode"
            @click="onFileModeTab('rename')"
          >
            <span v-if="renameMode" class="mode-dot" />
            文件重命名
          </button>
          <button
            type="button"
            class="mode-seg-btn"
            :class="{ active: mergeMode }"
            role="tab"
            :aria-selected="mergeMode"
            @click="onFileModeTab('folder-merge')"
          >
            <span v-if="mergeMode" class="mode-dot" />
            文件夹合并
          </button>
          <button
            type="button"
            class="mode-seg-btn"
            :class="{ active: transferMode }"
            role="tab"
            :aria-selected="transferMode"
            @click="onFileModeTab('transfer')"
          >
            <span v-if="transferMode" class="mode-dot" />
            文件传输
          </button>
        </div>
      </div>

      <SetupChecklist :context="checklistContext" />

      <div class="mr-workbench">
        <section class="panel-card browse-panel">
          <div class="panel-top">
            <div class="path-bar">
              <div class="path-trail">
                <el-icon class="path-folder"><Folder /></el-icon>
                <button type="button" class="path-seg" @click="goRoot">/</button>
                <template v-for="(p, idx) in displayPathParts" :key="idx">
                  <span class="path-slash">/</span>
                  <button
                    type="button"
                    class="path-seg"
                    :class="{ current: idx === displayPathParts.length - 1 }"
                    @click="goIndex(idx)"
                  >
                    {{ p }}
                  </button>
                </template>
              </div>
              <button type="button" class="icon-btn" title="复制路径" @click="copyCurrentPath">
                <el-icon><CopyDocument /></el-icon>
              </button>
            </div>

            <div class="tool-row">
              <div class="tool-left">
                <button type="button" class="tool-btn" @click="goRoot">
                  <el-icon><HomeFilled /></el-icon>
                  <span>根目录</span>
                </button>
                <button type="button" class="tool-btn" :disabled="!currentPath" @click="goParent">
                  <el-icon><Top /></el-icon>
                  <span>上级</span>
                </button>
                <button type="button" class="icon-btn tool-icon" title="刷新目录" @click="loadBrowse">
                  <el-icon><Refresh /></el-icon>
                </button>
                <button type="button" class="tool-btn accent" @click="createFolder">
                  <el-icon><Folder /></el-icon>
                  <span>新建文件夹</span>
                </button>
              </div>
              <div class="tool-right">
                <el-input
                  v-model="nameFilter"
                  clearable
                  placeholder="按文件名筛选..."
                  class="filter-input"
                  size="small"
                />
              </div>
            </div>

            <div class="browse-filters">
              <div class="type-chips">
                <button
                  type="button"
                  class="chip"
                  :class="{ active: typeFilter === 'all' }"
                  @click="typeFilter = 'all'"
                >
                  全部 ({{ typeCounts.all }})
                </button>
                <button
                  type="button"
                  class="chip"
                  :class="{ active: typeFilter === 'file' }"
                  @click="typeFilter = 'file'"
                >
                  仅文件 ({{ typeCounts.file }})
                </button>
                <button
                  type="button"
                  class="chip"
                  :class="{ active: typeFilter === 'dir' }"
                  @click="typeFilter = 'dir'"
                >
                  仅文件夹 ({{ typeCounts.dir }})
                </button>
              </div>
              <el-checkbox v-model="prefs.hideDotfiles" size="small">隐藏 . 开头文件</el-checkbox>
              <el-button v-if="renameMode" size="small" text @click="selectAllOfType('file')">全选文件</el-button>
              <el-button v-else-if="mergeMode" size="small" text @click="selectAllOfType('dir')">全选文件夹</el-button>
              <el-button v-else size="small" text @click="selectAllOfType('visible')">全选可见</el-button>
            </div>
          </div>

          <div class="mr-table-host">
            <el-table
              ref="tableRef"
              :key="currentPath"
              :data="filteredEntries"
              v-loading="browseLoading"
              row-key="path"
              height="100%"
              class="mr-file-table stitch-table"
              @selection-change="onSelectionChange"
              @row-dblclick="onRowDblClick"
            >
              <el-table-column type="selection" width="48" :selectable="selectable" />
              <el-table-column label="名称" min-width="220">
                <template #default="{ row }">
                  <div class="name-cell" :class="entryKind(row)">
                    <el-icon class="name-ic">
                      <Folder v-if="entryKind(row) === 'dir'" />
                      <VideoCamera v-else-if="entryKind(row) === 'video'" />
                      <Picture v-else-if="entryKind(row) === 'image'" />
                      <Document v-else />
                    </el-icon>
                    <button v-if="row.is_dir" type="button" class="name-link" @click="enterDir(row)">
                      {{ row.name }}
                    </button>
                    <span v-else class="name-text" :title="row.name">{{ row.name }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="大小" width="100" align="right" class-name="col-size">
                <template #default="{ row }">
                  <span class="size-cell">{{ row.is_dir ? "—" : formatBytes(row.size) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="110" align="center" class-name="col-status">
                <template #default="{ row }">
                  <span class="status-badge" :class="statusBadge(row).tone">
                    {{ statusBadge(row).text }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="mr-panel-footer stitch-footer">
            <div class="sel-summary">
              <span class="sel-dot" />
              <span>{{ selectionSummary }}</span>
              <span class="sel-mode">· {{ pageTitle }}</span>
            </div>
            <template v-if="renameMode">
              <div class="footer-actions">
                <el-button
                  v-if="!auth.user?.auto_rename_without_preview"
                  class="btn-emerald"
                  :loading="executeLoading"
                  :disabled="!canExecute || !previewId"
                  @click="runExecute()"
                >
                  确认执行重命名
                </el-button>
                <el-button
                  v-if="auth.user?.auto_rename_without_preview"
                  class="btn-emerald"
                  :loading="previewLoading || executeLoading"
                  :disabled="!selectedPaths.length"
                  @click="runAutoPipeline"
                >
                  全自动执行
                </el-button>
                <el-button
                  v-if="auth.user?.auto_rename_without_preview"
                  class="btn-emerald is-plain"
                  :loading="executeLoading"
                  :disabled="!canExecute"
                  @click="runExecute()"
                >
                  仅执行（已预览）
                </el-button>
                <el-button
                  type="primary"
                  class="btn-amber"
                  :loading="previewLoading"
                  :disabled="!selectedPaths.length"
                  @click="runPreview"
                >
                  <el-icon class="btn-ic"><MagicStick /></el-icon>
                  预览 AI 建议名
                </el-button>
              </div>
            </template>
            <template v-else-if="mergeMode">
              <div class="merge-block">
                <div class="merge-row">
                  <span class="merge-label">合并到目录</span>
                  <el-input
                    v-model="mergeTargetPath"
                    placeholder="相对挂载根路径，留空为根；不存在则自动创建"
                    clearable
                    class="merge-input"
                    size="small"
                  />
                  <el-button text type="primary" @click="useCurrentDirAsMergeTarget">使用当前目录</el-button>
                  <el-button text type="primary" @click="dirPickerOpen = true">选择目录…</el-button>
                </div>
                <el-button
                  type="warning"
                  :loading="mergeLoading"
                  :disabled="selectedPaths.length < 2"
                  @click="runMerge()"
                >
                  执行合并
                </el-button>
              </div>
            </template>
            <TransferPanel
              v-else
              ref="transferPanelRef"
              :selected-paths="selectedPaths"
              @done="onTransferDone"
            />
          </div>
        </section>

        <section v-if="renameMode" class="panel-card side-panel">
          <div class="side-head">
            <div class="side-head-left">
              <h2 class="side-title">预览与编辑</h2>
              <span class="side-badge">{{ previewRows.length ? `${previewRows.length} 条` : "重命名待命" }}</span>
            </div>
          </div>

          <div v-if="previewRows.length" class="preview-body">
            <div class="batch-row">
              <el-input v-model="batchPrefix" placeholder="前缀" clearable class="batch-field" size="small" />
              <el-input v-model="batchSuffix" placeholder="后缀（扩展名前）" clearable class="batch-field" size="small" />
              <el-button size="small" @click="applyBatchNames">应用到建议名</el-button>
            </div>
            <div class="mr-table-host preview-table">
              <el-table :data="previewRows" size="small" height="100%" class="mr-file-table">
                <el-table-column label="原文件名" min-width="120" prop="original_name" show-overflow-tooltip />
                <el-table-column label="建议新文件名" min-width="160">
                  <template #default="{ row }">
                    <el-input v-if="!row.error" v-model="row.suggested_name" size="small" />
                    <span v-else class="err">{{ row.error }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="preview-actions">
              <el-button
                class="btn-emerald"
                :loading="executeLoading"
                :disabled="!canExecute || (!previewId && !auth.user?.auto_rename_without_preview)"
                @click="runExecute()"
              >
                确认执行重命名
              </el-button>
            </div>
          </div>

          <div v-else class="side-empty">
            <div class="empty-icon-wrap">
              <el-icon class="empty-icon"><VideoCamera /></el-icon>
            </div>
            <h3 class="empty-title">尚未生成重命名方案预览</h3>
            <p class="empty-desc">
              在左侧目录中勾选需要处理的文件，点击底部的「预览 AI 建议名」。系统将调用元数据与模型，在此生成可编辑的标准化重命名方案。
            </p>
            <div class="rule-box">
              <div class="rule-box-head">
                <span>当前默认命名格式</span>
                <span class="rule-tag">TMDB MATCH</span>
              </div>
              <code class="rule-code"
                >{主标题} ({年份}) / {主标题} - S{季:02d}E{集:02d} - {副标题}.{后缀}</code
              >
            </div>
            <ul class="empty-bullets">
              <li>支持多文件智能分词、压制组及多版本 (Remux / WEB-DL) 识别</li>
              <li>预览结果可在表内直接微调建议名后再执行</li>
            </ul>
          </div>
        </section>

        <section v-else-if="mergeMode" class="panel-card side-panel hint-panel">
          <div class="side-head">
            <h2 class="side-title">合并说明</h2>
          </div>
          <ul class="merge-hint-list">
            <li>源文件夹不能互为父子关系（不要同时选外层与内层目录）。</li>
            <li>合并目标不能选在某个源文件夹内部。</li>
            <li>重名文件会依次命名为 <code>名称.ext</code>、<code>名称_1.ext</code>、<code>名称_2.ext</code>…</li>
            <li>源目录内文件全部移走后会删除原文件夹；若有文件移动失败则保留该源目录。</li>
          </ul>
        </section>

        <section v-else class="panel-card side-panel hint-panel">
          <div class="side-head">
            <h2 class="side-title">传输说明</h2>
          </div>
          <ul class="merge-hint-list">
            <li>传输目标在「系统配置 → 存储挂载」中维护，可配置多个。</li>
            <li>不能选择互为父子关系的路径。</li>
            <li>传输目标不能与挂载根相同，也不能落在所选源路径内部。</li>
            <li>文件重名自动加序号；同名文件夹会进入已有目录继续传输，不改文件夹名。</li>
            <li>上次选择的目标与传输方式会自动记住。</li>
          </ul>
        </section>
      </div>
    </template>

    <div v-else-if="!setupLoading" class="mr-setup-wrap">
      <el-card class="mr-setup-card" shadow="never">
        <div class="mr-setup-inner">
          <h2 class="mr-page-title">请先配置挂载目录</h2>
          <p class="mr-setup-desc">
            当前还没有可用的挂载根路径。配置完成后即可在此浏览文件并执行重命名 / 合并 / 传输。
          </p>
          <ol class="mr-setup-steps">
            <li>打开「系统配置 → 存储挂载」</li>
            <li>填写与 NAS / 容器映射一致的挂载根目录并保存</li>
            <li>返回本页开始浏览与操作</li>
          </ol>
          <div class="mr-setup-actions">
            <el-button type="primary" size="large" @click="goSettings">
              <el-icon class="btn-ic"><Setting /></el-icon>
              前往系统配置
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <DirPickerDialog v-model="dirPickerOpen" :initial-path="mergeTargetPath || currentPath" @confirm="onDirPicked" />
    <OpResultDialog
      v-model="resultOpen"
      :title="resultTitle"
      :results="resultItems"
      :can-retry="resultCanRetry"
      @retry="onResultRetry"
    />
  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 20px;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  font-size: clamp(1.35rem, 2.2vw, 1.65rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--mr-text);
}

.title-badge {
  font-family: var(--mr-font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  padding: 3px 8px;
  border-radius: 4px;
  color: var(--mr-text-muted);
  background: var(--surface-container, #222225);
}

.page-desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: var(--mr-text-secondary);
  line-height: 1.5;
}

.mode-seg {
  display: inline-flex;
  padding: 4px;
  border-radius: 12px;
  background: var(--surface-low, #1b1b1d);
  border: 1px solid rgba(255, 255, 255, 0.05);
  gap: 2px;
}

.mode-seg-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 7px 16px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--mr-text-secondary);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}

.mode-seg-btn:hover {
  color: var(--mr-text);
}

.mode-seg-btn.active {
  font-weight: 600;
  color: var(--mr-text);
  background: var(--surface-high, #2b2b2e);
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
}

.mode-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-primary);
}

.panel-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  border-radius: 12px;
  background: #18181b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
}

.panel-top {
  flex-shrink: 0;
  padding: 14px 16px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.path-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--surface-lowest, #0e0e10);
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-family: var(--mr-font-mono);
  font-size: 12px;
}

.path-trail {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  overflow-x: auto;
  white-space: nowrap;
  color: var(--mr-text-secondary);
}

.path-folder {
  color: var(--mr-text-muted);
  font-size: 15px;
  flex-shrink: 0;
}

.path-slash {
  color: var(--mr-text-muted);
}

.path-seg {
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.path-seg:hover {
  color: var(--el-color-primary);
}

.path-seg.current {
  color: var(--el-color-primary);
  font-weight: 600;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  margin: 0;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  background: var(--surface-container, #222225);
  color: var(--mr-text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.15s ease, background 0.15s ease;
}

.icon-btn:hover {
  color: var(--mr-text);
  background: var(--surface-high, #2b2b2e);
}

.tool-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tool-left,
.tool-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  background: var(--surface-container, #222225);
  color: var(--mr-text-secondary);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease;
}

.tool-btn:hover:not(:disabled) {
  color: var(--mr-text);
  background: var(--surface-high, #2b2b2e);
}

.tool-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tool-btn.accent {
  color: var(--mr-text);
}

.tool-btn.accent .el-icon {
  color: var(--el-color-primary);
}

.filter-input {
  width: 200px;
  max-width: 100%;
}

.browse-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
}

.type-chips {
  display: inline-flex;
  gap: 4px;
  padding: 2px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.2);
}

.chip {
  margin: 0;
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--mr-text-muted);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.chip.active {
  background: var(--surface-high, #2b2b2e);
  color: var(--mr-text);
  font-weight: 600;
}

.mr-table-host {
  padding: 0 4px;
}

.stitch-table :deep(.el-table__header th) {
  font-family: var(--mr-font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--mr-text-muted);
  background: transparent;
}

.stitch-table :deep(.el-table__row) {
  cursor: default;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.name-ic {
  flex-shrink: 0;
  font-size: 18px;
  color: var(--mr-text-muted);
}

.name-cell.dir .name-ic {
  color: var(--el-color-primary);
}

.name-link {
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--mr-text);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.name-link:hover {
  color: var(--el-color-primary);
}

.name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--mr-font-mono);
  font-size: 12.5px;
}

.size-cell {
  font-family: var(--mr-font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--mr-text-secondary);
  font-size: 12px;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: var(--mr-font-mono);
  font-size: 11px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: var(--surface-container, #222225);
  color: var(--mr-text-secondary);
}

.status-badge.pending {
  color: var(--el-color-primary);
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
}

.status-badge.asset {
  color: #ffbbc1;
  background: rgba(255, 187, 193, 0.08);
  border-color: rgba(255, 187, 193, 0.25);
}

.status-badge.meta {
  color: var(--mr-text-muted);
}

.stitch-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: color-mix(in srgb, #18181b 90%, #0e0e10);
}

.sel-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--mr-text-secondary);
  min-width: 0;
}

.sel-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
  flex-shrink: 0;
}

.sel-mode {
  color: var(--mr-text-muted);
  font-size: 12px;
}

.footer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.btn-ic {
  margin-right: 4px;
  vertical-align: middle;
}

.btn-amber.el-button--primary {
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.22);
}

.btn-amber.el-button--primary:not(:disabled):active {
  transform: scale(0.98);
}

.btn-emerald.el-button {
  background: rgba(16, 185, 129, 0.18) !important;
  border: 1px solid rgba(16, 185, 129, 0.35) !important;
  color: #10b981 !important;
  font-weight: 600;
}

.btn-emerald.el-button:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.28) !important;
  border-color: rgba(16, 185, 129, 0.5) !important;
  color: #34d399 !important;
}

.btn-emerald.el-button.is-disabled {
  opacity: 0.45;
}

.merge-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  align-items: flex-end;
}

.merge-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.merge-label {
  font-size: 13px;
  color: var(--mr-text-secondary);
  flex-shrink: 0;
}

.merge-input {
  flex: 1;
  min-width: 160px;
}

.side-panel {
  padding: 0;
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}

.side-head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.side-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--mr-text);
}

.side-badge {
  font-family: var(--mr-font-mono);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--el-color-primary);
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  white-space: nowrap;
}

.preview-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
  padding: 12px 16px 16px;
}

.batch-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.batch-field {
  width: 130px;
  max-width: 100%;
}

.preview-table {
  flex: 1;
  min-height: 160px;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.err {
  color: var(--el-color-danger);
  font-size: 12px;
}

.side-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 28px 20px;
  gap: 10px;
}

.empty-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.25);
  margin-bottom: 4px;
}

.empty-icon {
  font-size: 28px;
  color: var(--el-color-primary);
}

.empty-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--mr-text);
}

.empty-desc {
  margin: 0;
  max-width: 36ch;
  font-size: 13px;
  line-height: 1.6;
  color: var(--mr-text-secondary);
}

.rule-box {
  width: 100%;
  max-width: 360px;
  margin-top: 8px;
  padding: 12px;
  border-radius: 8px;
  background: var(--surface-lowest, #0e0e10);
  border: 1px solid rgba(255, 255, 255, 0.06);
  text-align: left;
}

.rule-box-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-family: var(--mr-font-mono);
  font-size: 10px;
  text-transform: uppercase;
  color: var(--mr-text-muted);
}

.rule-tag {
  color: var(--el-color-success);
}

.rule-code {
  display: block;
  font-family: var(--mr-font-mono);
  font-size: 11px;
  line-height: 1.55;
  color: var(--el-color-primary);
  word-break: break-all;
}

.empty-bullets {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  max-width: 36ch;
  text-align: left;
  font-size: 12px;
  color: var(--mr-text-secondary);
  line-height: 1.6;
}

.empty-bullets li {
  position: relative;
  padding-left: 14px;
}

.empty-bullets li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--el-color-primary);
}

.hint-panel {
  padding-bottom: 16px;
}

.hint-panel .merge-hint-list {
  margin: 0;
  padding: 8px 20px 0 32px;
  font-size: 13px;
  color: var(--mr-text-secondary);
  line-height: 1.75;
}

.merge-hint-list code {
  font-family: var(--mr-font-mono);
  font-size: 12px;
  background: var(--surface-container, #222225);
  padding: 1px 6px;
  border-radius: 4px;
}

@media (max-width: 1100px) {
  .panel-card {
    height: auto;
  }
}

@media (max-width: 720px) {
  .mode-seg {
    width: 100%;
  }
  .mode-seg-btn {
    flex: 1;
    justify-content: center;
    padding: 8px 6px;
    font-size: 12px;
  }
  .filter-input {
    width: 100%;
  }
  .tool-right {
    width: 100%;
  }
  .col-status {
    display: none;
  }
  .stitch-footer {
    flex-direction: column;
    align-items: stretch;
  }
  .footer-actions {
    width: 100%;
  }
  .footer-actions .el-button {
    flex: 1;
  }
}
</style>
