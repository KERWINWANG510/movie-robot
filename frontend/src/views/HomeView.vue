<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, nextTick, ref, watch } from "vue";

import http from "../api/http";
import { useAuthStore } from "../stores/auth";
import { useRouter } from "vue-router";

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
const router = useRouter();

function errMsg(e: unknown): string {
  if (typeof e === "object" && e !== null && "response" in e) {
    const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => JSON.stringify(x)).join("; ");
  }
  return "请求失败";
}

const currentPath = ref("");
const entries = ref<FileEntry[]>([]);
const browseLoading = ref(false);

const selectedPaths = ref<string[]>([]);
const previewRows = ref<PreviewRow[]>([]);
const previewId = ref<string | null>(null);
const previewLoading = ref(false);
const executeLoading = ref(false);

const breadcrumbParts = computed(() => {
  if (!currentPath.value) return [];
  return currentPath.value.split("/").filter(Boolean);
});

const autoSwitchLoading = ref(false);

async function onAutoChange(v: string | number | boolean) {
  const next = Boolean(v);
  autoSwitchLoading.value = true;
  try {
    await auth.updatePreference(next);
    ElMessage.success("偏好已保存");
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    autoSwitchLoading.value = false;
  }
}

function selectable(row: FileEntry) {
  return !row.is_dir;
}

async function loadBrowse() {
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
  selectedPaths.value = rows.filter((r) => !r.is_dir).map((r) => r.path);
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

async function logout() {
  await auth.logout();
  await router.replace({ name: "login" });
}

watch(
  currentPath,
  () => {
    loadBrowse();
  },
  { immediate: true },
);
</script>

<template>
  <div class="layout">
    <el-container class="shell">
      <el-header class="top" height="auto">
        <div class="top-inner">
          <div class="brand">
            <strong>智能文件重命名</strong>
            <span v-if="auth.user" class="sub">用户：{{ auth.user.username }}</span>
          </div>
          <div class="controls">
            <span class="hint">命名模式</span>
            <el-switch
              :model-value="auth.user?.auto_rename_without_preview ?? false"
              :loading="autoSwitchLoading"
              active-text="全自动"
              inactive-text="预览确认"
              inline-prompt
              style="margin-right: 8px"
              @change="onAutoChange"
            />
            <el-button @click="logout">退出</el-button>
          </div>
        </div>
      </el-header>

      <el-main class="main">
        <el-row :gutter="16">
          <el-col :xs="24" :lg="14">
            <el-card shadow="never">
              <template #header>
                <div class="card-head">
                  <span>浏览挂载目录</span>
                  <el-button text type="primary" @click="goRoot">根目录</el-button>
                  <el-button text type="primary" :disabled="!currentPath" @click="goParent">上级</el-button>
                  <el-button text type="primary" @click="loadBrowse">刷新</el-button>
                </div>
              </template>

              <el-breadcrumb separator="/" class="crumb">
                <el-breadcrumb-item>
                  <el-link type="primary" @click="goRoot">root</el-link>
                </el-breadcrumb-item>
                <el-breadcrumb-item v-for="(p, idx) in breadcrumbParts" :key="idx">
                  <el-link type="primary" @click="goIndex(idx)">{{ p }}</el-link>
                </el-breadcrumb-item>
              </el-breadcrumb>

              <el-table
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

              <div class="actions">
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
              <p class="tips">
                「预览确认」模式下需先预览；执行时会校验预览会话。全自动模式下可不强制预览会话，但仍建议先预览检查。
              </p>
            </el-card>
          </el-col>

          <el-col :xs="24" :lg="10">
            <el-card shadow="never">
              <template #header>
                <span>预览与编辑</span>
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
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.shell {
  max-width: 1280px;
  margin: 0 auto;
}
.top {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
}
.top-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.brand .sub {
  margin-left: 12px;
  color: #909399;
  font-size: 13px;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.hint {
  font-size: 13px;
  color: #606266;
}
.main {
  padding: 16px;
}
.card-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.crumb {
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tips {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
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
