<script setup lang="ts">
import { Setting } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import http from "../api/http";
import { useAuthStore } from "../stores/auth";

type FileEntry = { name: string; path: string; is_dir: boolean };

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

function errMsg(e: unknown): string {
  if (typeof e === "object" && e !== null && "response" in e) {
    const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => JSON.stringify(x)).join("; ");
  }
  return "请求失败";
}

/** 挂载根可用时才展示浏览与预览；否则引导去系统配置 */
const mountReady = ref(false);
const setupLoading = ref(true);

const currentPath = ref("");
const entries = ref<FileEntry[]>([]);
const browseLoading = ref(false);

const selectedPaths = ref<string[]>([]);
/** 由路由决定：folder-merge 勾选目录；rename 勾选文件 */
const mergeMode = computed(() => route.name === "folder-merge");
const mergeTargetPath = ref("");
const mergeLoading = ref(false);
const previewRows = ref<PreviewRow[]>([]);
const previewId = ref<string | null>(null);
const previewLoading = ref(false);
const executeLoading = ref(false);

const breadcrumbParts = computed(() => {
  if (!currentPath.value) return [];
  return currentPath.value.split("/").filter(Boolean);
});

async function refreshMountAndBrowse() {
  setupLoading.value = true;
  try {
    const { data } = await http.get<{ mount_ready: boolean }>("/settings");
    mountReady.value = data.mount_ready;
    currentPath.value = "";
    if (data.mount_ready) {
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

/** 切换「文件重命名 / 文件夹合并」时保留当前浏览路径，仅同步挂载状态与列表 */
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
      await refreshMountAndBrowse();
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
  } catch (e: unknown) {
    const msg = errMsg(e);
    ElMessage.error(msg);
  } finally {
    browseLoading.value = false;
  }
}

function enterDir(row: FileEntry) {
  if (!row.is_dir) return;
  currentPath.value = row.path;
}

function goRoot() {
  currentPath.value = "";
}

function goIndex(idx: number) {
  const parts = breadcrumbParts.value.slice(0, idx + 1);
  currentPath.value = parts.join("/");
}

function goParent() {
  if (!currentPath.value) return;
  const parts = currentPath.value.split("/").filter(Boolean);
  parts.pop();
  currentPath.value = parts.join("/");
}

function onSelectionChange(rows: FileEntry[]) {
  if (mergeMode.value) {
    selectedPaths.value = rows.filter((r) => r.is_dir).map((r) => r.path);
  } else {
    selectedPaths.value = rows.filter((r) => !r.is_dir).map((r) => r.path);
  }
}

function useCurrentDirAsMergeTarget() {
  mergeTargetPath.value = currentPath.value;
}

async function runMerge() {
  if (selectedPaths.value.length < 2) {
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
      source_paths: selectedPaths.value,
      target_path: mergeTargetPath.value.trim(),
    });
    if (data.failed_count === 0) {
      ElMessage.success(`已合并 ${data.moved_count} 个文件`);
    } else {
      ElMessage.warning(`完成：成功 ${data.moved_count}，失败 ${data.failed_count}`);
    }
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

async function runExecute() {
  if (!canExecute.value) {
    ElMessage.warning("请完善预览结果中的新文件名");
    return;
  }
  const auto = auth.user?.auto_rename_without_preview ?? false;
  if (!auto && !previewId.value) {
    ElMessage.warning("请先完成预览，或开启全自动模式");
    return;
  }
  const items = previewRows.value
    .filter((r) => !r.error)
    .map((r) => ({ path: r.path, new_name: r.suggested_name.trim() }));

  executeLoading.value = true;
  try {
    const { data } = await http.post<{ results: { path: string; ok: boolean; message: string | null }[] }>(
      "/rename/execute",
      {
        preview_id: auto ? null : previewId.value,
        items,
      },
    );
    const failed = data.results.filter((x) => !x.ok);
    if (failed.length === 0) ElMessage.success("重命名完成");
    else ElMessage.warning(`部分失败：${failed.map((f) => f.path).join("、")}`);
    previewRows.value = [];
    previewId.value = null;
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

function goSettings() {
  router.push({ name: "settings-storage" });
}

watch(currentPath, () => {
  if (mountReady.value) {
    loadBrowse();
  }
});

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
      <div class="mr-page-intro">
        <h2 class="mr-page-title">{{ pageTitle }}</h2>
        <p class="mr-page-desc">{{ pageDesc }}</p>
      </div>
      <el-row :gutter="18">
        <el-col :xs="24" :lg="14">
          <el-card class="panel-card" shadow="never">
            <template #header>
              <div class="mr-card-head">
                <span>浏览挂载目录</span>
                <el-button text type="primary" @click="goRoot">根目录</el-button>
                <el-button text type="primary" :disabled="!currentPath" @click="goParent">上级</el-button>
                <el-button text type="primary" @click="loadBrowse">刷新</el-button>
              </div>
            </template>

            <el-breadcrumb separator="/" class="mr-crumb">
              <el-breadcrumb-item>
                <el-link type="primary" @click="goRoot">root</el-link>
              </el-breadcrumb-item>
              <el-breadcrumb-item v-for="(p, idx) in breadcrumbParts" :key="idx">
                <el-link type="primary" @click="goIndex(idx)">{{ p }}</el-link>
              </el-breadcrumb-item>
            </el-breadcrumb>

            <el-table
              :key="String(route.name)"
              :data="entries"
              v-loading="browseLoading"
              row-key="path"
              height="360"
              class="file-table"
              @selection-change="onSelectionChange"
            >
              <el-table-column type="selection" width="48" :selectable="selectable" />
              <el-table-column label="名称" min-width="160">
                <template #default="{ row }">
                  <el-link v-if="row.is_dir" type="primary" @click="enterDir(row)">{{ row.name }}/</el-link>
                  <span v-else>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="路径" prop="path" min-width="220" show-overflow-tooltip />
            </el-table>

            <template v-if="!mergeMode">
              <div class="mr-actions">
                <el-button type="primary" :loading="previewLoading" @click="runPreview">预览 AI 建议名</el-button>
                <el-button
                  v-if="auth.user?.auto_rename_without_preview"
                  type="success"
                  :loading="previewLoading || executeLoading"
                  @click="runAutoPipeline"
                >
                  全自动：预览并立即执行
                </el-button>
                <el-button
                  v-if="!auth.user?.auto_rename_without_preview"
                  type="success"
                  :loading="executeLoading"
                  :disabled="!canExecute || !previewId"
                  @click="runExecute"
                >
                  确认执行重命名
                </el-button>
                <el-button
                  v-if="auth.user?.auto_rename_without_preview"
                  type="success"
                  plain
                  :loading="executeLoading"
                  :disabled="!canExecute"
                  @click="runExecute"
                >
                  仅执行（已预览）
                </el-button>
              </div>
              <p class="mr-tips">
                「预览确认」模式下需先预览；执行时会校验预览会话。全自动模式下可不强制预览会话，但仍建议先预览检查。
              </p>
            </template>
            <template v-else>
              <div class="merge-panel">
                <div class="merge-row">
                  <span class="merge-label">合并到目录</span>
                  <el-input
                    v-model="mergeTargetPath"
                    placeholder="相对挂载根的路径，留空为根目录；不存在时自动创建（支持 test/test2 多级）"
                    clearable
                    class="merge-input"
                  />
                  <el-button text type="primary" @click="useCurrentDirAsMergeTarget">使用当前目录</el-button>
                </div>
                <p class="mr-tips merge-tips">
                  勾选两个或以上文件夹；各文件夹内所有层级的文件会移动到目标目录下（不保留子目录结构）。目标目录若不存在会自动创建。
                </p>
                <el-button type="warning" :loading="mergeLoading" :disabled="selectedPaths.length < 2" @click="runMerge">
                  执行合并
                </el-button>
              </div>
            </template>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="10">
          <el-card v-if="!mergeMode" class="panel-card" shadow="never">
            <template #header>
              <div class="mr-card-head"><span>预览与编辑</span></div>
            </template>
            <el-table :data="previewRows" size="small" max-height="420">
              <el-table-column label="原文件名" min-width="120" prop="original_name" show-overflow-tooltip />
              <el-table-column label="建议新文件名" min-width="160">
                <template #default="{ row }">
                  <el-input v-if="!row.error" v-model="row.suggested_name" />
                  <span v-else class="err">{{ row.error }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
          <el-card v-else shadow="never" class="panel-card merge-hint-card">
            <template #header>
              <div class="mr-card-head"><span>合并说明</span></div>
            </template>
            <ul class="merge-hint-list">
              <li>源文件夹不能互为父子关系（不要同时选外层与内层目录）。</li>
              <li>合并目标不能选在某个源文件夹内部。</li>
              <li>重名文件会依次命名为 <code>名称.ext</code>、<code>名称_1.ext</code>、<code>名称_2.ext</code>…</li>
            </ul>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <div v-else-if="!setupLoading" class="mr-setup-wrap">
      <el-card class="mr-setup-card" shadow="hover">
        <div class="mr-setup-inner">
          <h2 class="mr-page-title">请先配置挂载目录</h2>
          <p class="mr-setup-desc">
            当前还没有可用的挂载根路径（路径不存在或不是文件夹）。请在系统配置中填写并保存「挂载根目录」，确保该路径在服务端可访问。
          </p>
          <el-button type="primary" size="large" @click="goSettings">
            <el-icon class="btn-ic"><Setting /></el-icon>
            前往系统配置
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  max-width: 1280px;
  margin: 0 auto;
  min-height: 240px;
}

.panel-card {
  border-radius: var(--mr-radius-md);
}

.panel-card :deep(.el-card__header) {
  padding: 14px 18px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.btn-ic {
  margin-right: 6px;
  vertical-align: middle;
}

.merge-panel {
  margin-top: 12px;
}

.merge-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.merge-label {
  font-size: 14px;
  color: var(--mr-text-secondary);
  flex-shrink: 0;
}

.merge-input {
  flex: 1;
  min-width: 200px;
}

.merge-tips {
  margin-bottom: 12px;
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
.err {
  color: var(--el-color-danger);
}
.file-table {
  width: 100%;
}

@media (max-width: 992px) {
  .file-table {
    height: auto !important;
  }
}
</style>
