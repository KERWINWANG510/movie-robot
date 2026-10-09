<script setup lang="ts">
import { Setting } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type TableInstance } from "element-plus";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import http from "../api/http";
import DirPickerDialog from "../components/DirPickerDialog.vue";
import OpResultDialog, { type OpResultItem } from "../components/OpResultDialog.vue";
import SetupChecklist from "../components/SetupChecklist.vue";
import { useBrowsePath } from "../composables/useBrowsePath";
import { useAuthStore } from "../stores/auth";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { errMsg } from "../utils/errMsg";
import { formatBytes } from "../utils/formatBytes";
import { parentRelPath } from "../utils/path";

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

const mergeMode = computed(() => route.name === "folder-merge");
const mergeTargetPath = ref("");
const mergeLoading = ref(false);
const dirPickerOpen = ref(false);

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

watch(
  () => route.name,
  async (name, oldName) => {
    if (name !== "rename" && name !== "folder-merge") return;

    if (oldName === undefined) {
      await refreshMountAndBrowse(false);
      return;
    }

    selectedPaths.value = [];
    if (name === "folder-merge") {
      previewRows.value = [];
      previewId.value = null;
      mergeTargetPath.value = currentPath.value;
    }

    await syncMountAndCurrentBrowse();
  },
  { immediate: true },
);

function selectable(row: FileEntry) {
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
  if (mergeMode.value) {
    selectedPaths.value = rows.filter((r) => r.is_dir).map((r) => r.path);
  } else {
    selectedPaths.value = rows.filter((r) => !r.is_dir).map((r) => r.path);
  }
}

function selectAllOfType(kind: "file" | "dir") {
  const table = tableRef.value;
  if (!table) return;
  table.clearSelection();
  for (const row of filteredEntries.value) {
    if (kind === "dir" ? row.is_dir : !row.is_dir) {
      if (selectable(row)) table.toggleRowSelection(row, true);
    }
  }
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
      "将把所选各文件夹内（含子文件夹）的全部文件移动到目标目录下，同名文件会自动加 _1、_2 等后缀。此操作会移动真实文件，是否继续？",
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
    if (mergeMode.value) {
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

const pageTitle = computed(() => (mergeMode.value ? "文件夹合并" : "文件重命名"));
const pageDesc = computed(() =>
  mergeMode.value
    ? "勾选多个文件夹，将其中的文件（递归）扁平移动到目标目录；重名自动加序号。挂载与模型在「系统配置」。"
    : "勾选文件后预览 AI 建议名并执行重命名。挂载路径与模型请在「系统配置」中设置。",
);
</script>

<template>
  <div class="home-page" v-loading="setupLoading">
    <template v-if="mountReady">
      <div class="mr-page-intro is-compact">
        <div>
          <h2 class="mr-page-title">{{ pageTitle }}</h2>
          <p class="mr-page-desc">{{ pageDesc }}</p>
        </div>
      </div>

      <SetupChecklist :context="mergeMode ? 'merge' : 'rename'" />

      <div class="mr-workbench">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="mr-card-head">
              <span>浏览挂载目录</span>
              <span class="head-spacer" />
              <span class="head-meta">已选 {{ selectedPaths.length }} 项</span>
              <el-button text type="primary" @click="goRoot">根目录</el-button>
              <el-button text type="primary" :disabled="!currentPath" @click="goParent">上级</el-button>
              <el-button text type="primary" @click="loadBrowse">刷新</el-button>
            </div>
          </template>

          <div class="mr-panel-toolbar">
            <el-breadcrumb separator="/" class="mr-crumb">
              <el-breadcrumb-item>
                <el-link type="primary" @click="goRoot">root</el-link>
              </el-breadcrumb-item>
              <el-breadcrumb-item v-for="(p, idx) in breadcrumbParts" :key="idx">
                <el-link type="primary" @click="goIndex(idx)">{{ p }}</el-link>
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>

          <div class="browse-filters">
            <el-input
              v-model="nameFilter"
              clearable
              placeholder="按名称过滤"
              class="filter-input"
            />
            <el-radio-group v-model="typeFilter" size="small">
              <el-radio-button value="all">全部</el-radio-button>
              <el-radio-button value="file">仅文件</el-radio-button>
              <el-radio-button value="dir">仅文件夹</el-radio-button>
            </el-radio-group>
            <el-checkbox v-model="prefs.hideDotfiles" size="small">隐藏点文件</el-checkbox>
            <el-button
              v-if="!mergeMode"
              size="small"
              @click="selectAllOfType('file')"
            >
              全选文件
            </el-button>
            <el-button
              v-else
              size="small"
              @click="selectAllOfType('dir')"
            >
              全选文件夹
            </el-button>
          </div>

          <div class="mr-table-host">
            <el-table
              ref="tableRef"
              :key="String(route.name) + currentPath"
              :data="filteredEntries"
              v-loading="browseLoading"
              row-key="path"
              height="100%"
              class="mr-file-table"
              @selection-change="onSelectionChange"
              @row-dblclick="onRowDblClick"
            >
              <el-table-column type="selection" width="48" :selectable="selectable" />
              <el-table-column label="名称" min-width="180">
                <template #default="{ row }">
                  <el-link v-if="row.is_dir" type="primary" @click="enterDir(row)">{{ row.name }}/</el-link>
                  <span v-else>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="大小" width="100" align="right" class-name="col-size">
                <template #default="{ row }">
                  <span class="size-cell">{{ row.is_dir ? "—" : formatBytes(row.size) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="路径" prop="path" min-width="160" show-overflow-tooltip class-name="col-path" />
            </el-table>
          </div>

          <div class="mr-panel-footer">
            <template v-if="!mergeMode">
              <div class="mr-actions">
                <el-button type="primary" :loading="previewLoading" :disabled="!selectedPaths.length" @click="runPreview">
                  预览 AI 建议名
                </el-button>
                <el-button
                  v-if="auth.user?.auto_rename_without_preview"
                  type="success"
                  :loading="previewLoading || executeLoading"
                  :disabled="!selectedPaths.length"
                  @click="runAutoPipeline"
                >
                  全自动执行
                </el-button>
                <el-button
                  v-if="!auth.user?.auto_rename_without_preview"
                  type="success"
                  :loading="executeLoading"
                  :disabled="!canExecute || !previewId"
                  @click="runExecute()"
                >
                  确认执行重命名
                </el-button>
                <el-button
                  v-if="auth.user?.auto_rename_without_preview"
                  type="success"
                  plain
                  :loading="executeLoading"
                  :disabled="!canExecute"
                  @click="runExecute()"
                >
                  仅执行（已预览）
                </el-button>
              </div>
            </template>
            <template v-else>
              <div class="merge-row">
                <span class="merge-label">合并到目录</span>
                <el-input
                  v-model="mergeTargetPath"
                  placeholder="相对挂载根路径，留空为根；不存在则自动创建"
                  clearable
                  class="merge-input"
                />
                <el-button text type="primary" @click="useCurrentDirAsMergeTarget">使用当前目录</el-button>
                <el-button text type="primary" @click="dirPickerOpen = true">选择目录…</el-button>
              </div>
              <div class="mr-actions" style="margin-top: 10px">
                <el-button type="warning" :loading="mergeLoading" :disabled="selectedPaths.length < 2" @click="runMerge()">
                  执行合并
                </el-button>
              </div>
              <p class="mr-tips">勾选两个或以上文件夹；文件会扁平移动到目标目录（不保留子目录结构）。</p>
            </template>
          </div>
        </el-card>

        <el-card v-if="!mergeMode" class="panel-card" shadow="never">
          <template #header>
            <div class="mr-card-head">
              <span>预览与编辑</span>
              <span class="head-spacer" />
              <span v-if="previewRows.length" class="head-meta">{{ previewRows.length }} 条</span>
            </div>
          </template>
          <div v-if="previewRows.length" class="preview-body">
            <div class="batch-row">
              <el-input v-model="batchPrefix" placeholder="前缀" clearable class="batch-field" />
              <el-input v-model="batchSuffix" placeholder="后缀（扩展名前）" clearable class="batch-field" />
              <el-button size="small" @click="applyBatchNames">应用到建议名</el-button>
            </div>
            <div class="mr-table-host preview-table">
              <el-table :data="previewRows" size="small" height="100%" class="mr-file-table">
                <el-table-column label="原文件名" min-width="120" prop="original_name" show-overflow-tooltip />
                <el-table-column label="建议新文件名" min-width="160">
                  <template #default="{ row }">
                    <el-input v-if="!row.error" v-model="row.suggested_name" />
                    <span v-else class="err">{{ row.error }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div class="preview-actions">
              <el-button
                type="success"
                :loading="executeLoading"
                :disabled="!canExecute || (!previewId && !auth.user?.auto_rename_without_preview)"
                @click="runExecute()"
              >
                确认执行重命名
              </el-button>
            </div>
          </div>
          <div v-else class="mr-side-empty">
            <strong>尚未生成预览</strong>
            在左侧勾选文件后点击「预览 AI 建议名」，结果将显示在此处，可直接编辑。
          </div>
        </el-card>

        <el-card v-else class="panel-card merge-hint-card" shadow="never">
          <template #header>
            <div class="mr-card-head"><span>合并说明</span></div>
          </template>
          <ul class="merge-hint-list">
            <li>源文件夹不能互为父子关系（不要同时选外层与内层目录）。</li>
            <li>合并目标不能选在某个源文件夹内部。</li>
            <li>重名文件会依次命名为 <code>名称.ext</code>、<code>名称_1.ext</code>、<code>名称_2.ext</code>…</li>
          </ul>
        </el-card>
      </div>
    </template>

    <div v-else-if="!setupLoading" class="mr-setup-wrap">
      <el-card class="mr-setup-card" shadow="never">
        <div class="mr-setup-inner">
          <h2 class="mr-page-title">请先配置挂载目录</h2>
          <p class="mr-setup-desc">
            当前还没有可用的挂载根路径。配置完成后即可在此浏览文件并执行重命名 / 合并。
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
}

.panel-card {
  border-radius: var(--mr-radius-md);
  border: 1px solid var(--mr-border-soft);
}

.panel-card :deep(.el-card__header) {
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  background: var(--color-muted);
}

.btn-ic {
  margin-right: 6px;
  vertical-align: middle;
}

.browse-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 0 0 10px;
}

.filter-input {
  width: 180px;
  max-width: 100%;
}

.merge-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.merge-label {
  font-size: 13px;
  color: var(--mr-text-secondary);
  flex-shrink: 0;
}

.merge-input {
  flex: 1;
  min-width: 180px;
}

.merge-hint-card .merge-hint-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
  color: var(--mr-text-secondary);
  line-height: 1.7;
}

.merge-hint-list code {
  font-size: 12px;
  background: var(--el-fill-color-light);
  padding: 1px 6px;
  border-radius: 4px;
}

.preview-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
}

.batch-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.batch-field {
  width: 140px;
  max-width: 100%;
}

.preview-table {
  flex: 1;
  min-height: 160px;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
  border-top: 1px solid var(--el-border-color-extra-light);
}

.err {
  color: var(--el-color-danger);
}

.size-cell {
  font-variant-numeric: tabular-nums;
  color: var(--mr-text-secondary);
  font-size: 13px;
}

@media (max-width: 720px) {
  .panel-card :deep(.col-path) {
    display: none;
  }
}
</style>
