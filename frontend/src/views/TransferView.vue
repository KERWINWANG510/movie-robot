<script setup lang="ts">
import { Setting, Upload } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox, type TableInstance } from "element-plus";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import http from "../api/http";
import OpResultDialog, { type OpResultItem } from "../components/OpResultDialog.vue";
import SetupChecklist from "../components/SetupChecklist.vue";
import { useBrowsePath } from "../composables/useBrowsePath";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { errMsg } from "../utils/errMsg";
import { parentRelPath } from "../utils/path";

type FileEntry = { name: string; path: string; is_dir: boolean };

type BrowseResponse = {
  path: string;
  entries: FileEntry[];
};

type TransferDest = { id: number; label: string; path: string; ready: boolean };

const router = useRouter();
const route = useRoute();
const prefs = useBrowsePrefsStore();
const { currentPath, breadcrumbParts, setPath, hydrateFromStorage } = useBrowsePath();

const mountReady = ref(false);
const transferDestinations = ref<TransferDest[]>([]);
const selectedDestinationId = ref<number | null>(null);
const setupLoading = ref(true);

const entries = ref<FileEntry[]>([]);
const browseLoading = ref(false);
const nameFilter = ref("");
const typeFilter = ref<"all" | "file" | "dir">("all");
const tableRef = ref<TableInstance>();

const selectedPaths = ref<string[]>([]);
const transferLoading = ref(false);

const resultOpen = ref(false);
const resultItems = ref<OpResultItem[]>([]);
const resultCanRetry = ref(false);
let lastTransferPayload: {
  paths: string[];
  mode: "copy" | "move";
  destination_id: number;
} | null = null;

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

const needMountSetup = computed(() => !mountReady.value);
const hasAnyDestination = computed(() => transferDestinations.value.length > 0);
const hasReadyDestination = computed(() => transferDestinations.value.some((d) => d.ready));

const selectedDest = computed(
  () => transferDestinations.value.find((d) => d.id === selectedDestinationId.value) ?? null,
);

const transferAllowed = computed(
  () => Boolean(selectedDest.value?.ready && selectedPaths.value.length > 0),
);

function pickDestination(list: TransferDest[]) {
  const saved = prefs.savedTransferDestId;
  if (saved != null) {
    const hit = list.find((d) => d.id === saved && d.ready);
    if (hit) {
      selectedDestinationId.value = hit.id;
      return;
    }
  }
  const firstReady = list.find((d) => d.ready);
  selectedDestinationId.value = firstReady?.id ?? list[0]?.id ?? null;
}

async function refreshSettingsAndBrowse() {
  setupLoading.value = true;
  try {
    const { data } = await http.get<{ mount_ready: boolean; transfer_destinations: TransferDest[] }>("/settings");
    mountReady.value = data.mount_ready;
    transferDestinations.value = data.transfer_destinations ?? [];
    pickDestination(transferDestinations.value);
    if (data.mount_ready) {
      hydrateFromStorage();
      await loadBrowse();
    } else {
      entries.value = [];
      selectedPaths.value = [];
    }
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
    mountReady.value = false;
    transferDestinations.value = [];
    selectedDestinationId.value = null;
  } finally {
    setupLoading.value = false;
  }
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
  selectedPaths.value = rows.map((r) => r.path);
}

function selectAllVisible() {
  const table = tableRef.value;
  if (!table) return;
  table.clearSelection();
  for (const row of filteredEntries.value) {
    table.toggleRowSelection(row, true);
  }
}

function goSettings() {
  prefs.setReturnTo(route.fullPath);
  router.push({ name: "settings-storage" });
}

function openTargetInBrowse() {
  /* 传输目标是绝对路径，不一定在挂载根内；能做的是跳到重命名页并提示 */
  ElMessage.info("传输目标为外部目录时无法在挂载浏览中打开；请在系统配置中查看目标路径。");
}

watch(currentPath, () => {
  if (mountReady.value) void loadBrowse();
});

watch(selectedDestinationId, (id) => {
  if (id != null) prefs.savedTransferDestId = id;
});

async function runTransfer(pathsOverride?: string[]) {
  const paths = pathsOverride ?? selectedPaths.value;
  if (paths.length === 0) {
    ElMessage.warning("请先勾选要传输的文件或文件夹");
    return;
  }
  if (!selectedDestinationId.value || !selectedDest.value?.ready) {
    ElMessage.warning("请选择一个可用的传输目标（路径须已存在且为目录）");
    return;
  }
  const mode = prefs.transferMode;
  const verb = mode === "copy" ? "复制" : "移动";
  const label = selectedDest.value.label;
  const skipConfirm = mode === "copy" && prefs.skipCopyConfirm;
  if (!skipConfirm) {
    try {
      await ElMessageBox.confirm(
        `将把所选 ${paths.length} 项${verb}到「${label}」。目标侧重名会自动加 _1、_2 等后缀；目录整体传输时若重名则使用 foo_1 形式。是否继续？`,
        `文件传输（${verb}）`,
        { type: "warning", confirmButtonText: "开始传输", cancelButtonText: "取消" },
      );
    } catch {
      return;
    }
  }
  transferLoading.value = true;
  const payload = {
    paths,
    mode,
    destination_id: selectedDestinationId.value,
  };
  try {
    const { data } = await http.post<{
      results: { source_path: string; dest_path: string; ok: boolean; message: string | null }[];
      ok_count: number;
      failed_count: number;
    }>("/files/transfer", payload);
    const items: OpResultItem[] = data.results.map((r, i) => ({
      key: `${r.source_path}-${i}`,
      source: r.source_path,
      dest: r.dest_path,
      ok: r.ok,
      message: r.message,
    }));
    if (data.failed_count === 0) {
      ElMessage.success(`已传输 ${data.ok_count} 项`);
    } else {
      ElMessage.warning(`完成：成功 ${data.ok_count}，失败 ${data.failed_count}`);
    }
    lastTransferPayload = payload;
    resultItems.value = items;
    resultCanRetry.value = data.failed_count > 0;
    resultOpen.value = true;
    selectedPaths.value = [];
    await loadBrowse();
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    transferLoading.value = false;
  }
}

async function onResultRetry(failed: OpResultItem[]) {
  resultOpen.value = false;
  if (!lastTransferPayload) return;
  const paths = failed.map((f) => f.source);
  await runTransfer(paths);
}

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
  if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter" && transferAllowed.value) {
    void runTransfer();
  }
}

onMounted(() => {
  window.addEventListener("keydown", onKeydown);
  void refreshSettingsAndBrowse();
});
onUnmounted(() => window.removeEventListener("keydown", onKeydown));
</script>

<template>
  <div class="transfer-page" v-loading="setupLoading">
    <template v-if="mountReady">
      <div class="mr-page-intro is-compact">
        <div>
          <h2 class="mr-page-title">文件传输</h2>
          <p class="mr-page-desc">
            多选文件或文件夹，选择目标后复制 / 剪切到对应目录；名称冲突时自动加序号。
          </p>
        </div>
      </div>

      <SetupChecklist context="transfer" />

      <el-alert v-if="!hasAnyDestination" type="warning" :closable="false" class="mb-alert" show-icon>
        <template #title>尚未配置传输目标</template>
        请先在「系统配置 → 存储挂载」中添加至少一个传输目标，保存后即可选择。
        <div class="alert-actions">
          <el-button type="primary" size="small" @click="goSettings">前往系统配置</el-button>
        </div>
      </el-alert>
      <el-alert
        v-else-if="!hasReadyDestination"
        type="warning"
        :closable="false"
        class="mb-alert"
        show-icon
      >
        <template #title>当前没有可用的传输目标</template>
        已配置的目录在服务端不存在或不可访问。请检查挂载、权限与路径。
        <div class="alert-actions">
          <el-button type="primary" size="small" @click="goSettings">前往系统配置</el-button>
        </div>
      </el-alert>

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
            <el-input v-model="nameFilter" clearable placeholder="按名称过滤" class="filter-input" />
            <el-radio-group v-model="typeFilter" size="small">
              <el-radio-button value="all">全部</el-radio-button>
              <el-radio-button value="file">仅文件</el-radio-button>
              <el-radio-button value="dir">仅文件夹</el-radio-button>
            </el-radio-group>
            <el-checkbox v-model="prefs.hideDotfiles" size="small">隐藏点文件</el-checkbox>
            <el-button size="small" @click="selectAllVisible">全选可见</el-button>
          </div>

          <div class="mr-table-host">
            <el-table
              ref="tableRef"
              :key="currentPath"
              :data="filteredEntries"
              v-loading="browseLoading"
              row-key="path"
              height="100%"
              class="mr-file-table"
              @selection-change="onSelectionChange"
              @row-dblclick="onRowDblClick"
            >
              <el-table-column type="selection" width="48" />
              <el-table-column label="名称" min-width="180">
                <template #default="{ row }">
                  <el-link v-if="row.is_dir" type="primary" @click="enterDir(row)">{{ row.name }}/</el-link>
                  <span v-else>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="路径" prop="path" min-width="160" show-overflow-tooltip class-name="col-path" />
            </el-table>
          </div>

          <div class="mr-panel-footer">
            <div class="dest-select-row">
              <span class="mode-label">传输目标</span>
              <el-select
                v-model="selectedDestinationId"
                placeholder="请选择传输目标"
                class="dest-select"
                filterable
                :disabled="!hasAnyDestination"
              >
                <el-option
                  v-for="d in transferDestinations"
                  :key="d.id"
                  :label="d.ready ? d.label : `${d.label}（路径不可用）`"
                  :value="d.id"
                  :disabled="!d.ready"
                />
              </el-select>
            </div>
            <div class="mode-row">
              <span class="mode-label">传输方式</span>
              <el-radio-group v-model="prefs.transferMode">
                <el-radio-button value="copy">复制</el-radio-button>
                <el-radio-button value="move">剪切</el-radio-button>
              </el-radio-group>
              <el-checkbox
                v-if="prefs.transferMode === 'copy'"
                v-model="prefs.skipCopyConfirm"
                size="small"
              >
                复制时跳过确认
              </el-checkbox>
            </div>
            <div class="mr-actions" style="margin-top: 10px">
              <el-button type="primary" :loading="transferLoading" :disabled="!transferAllowed" @click="runTransfer()">
                <el-icon class="btn-ic"><Upload /></el-icon>
                传输到所选目标
              </el-button>
              <el-button text type="primary" @click="openTargetInBrowse">查看目标说明</el-button>
            </div>
            <p class="mr-tips">剪切会移动原路径；目标已存在同名项时自动使用 _1、_2 等后缀。</p>
          </div>
        </el-card>

        <el-card class="panel-card hint-card" shadow="never">
          <template #header>
            <div class="mr-card-head"><span>说明</span></div>
          </template>
          <ul class="hint-list">
            <li>传输目标在「系统配置 → 存储挂载」中维护，可配置多个。</li>
            <li>不能选择互为父子关系的路径。</li>
            <li>传输目标不能与挂载根相同，也不能落在所选源路径内部。</li>
            <li>上次选择的目标与传输方式会自动记住。</li>
          </ul>
        </el-card>
      </div>
    </template>

    <div v-else-if="!setupLoading && needMountSetup" class="mr-setup-wrap">
      <el-card class="mr-setup-card" shadow="never">
        <div class="mr-setup-inner">
          <h2 class="mr-page-title">请先配置挂载目录</h2>
          <p class="mr-setup-desc">配置挂载根与传输目标后，即可在此浏览并传输文件。</p>
          <ol class="mr-setup-steps">
            <li>打开「系统配置 → 存储挂载」</li>
            <li>填写挂载根目录，并添加至少一个传输目标</li>
            <li>返回本页选择文件并传输</li>
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

    <OpResultDialog
      v-model="resultOpen"
      title="文件传输结果"
      :results="resultItems"
      :can-retry="resultCanRetry"
      @retry="onResultRetry"
    />
  </div>
</template>

<style scoped>
.transfer-page {
  width: 100%;
  min-height: 100%;
}

.mb-alert {
  margin-bottom: 12px;
  border-radius: var(--mr-radius-md);
}

.mb-alert :deep(.el-alert__title) {
  font-weight: 600;
}

.alert-actions {
  margin-top: 10px;
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

.dest-select-row,
.mode-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.mode-row {
  margin-top: 10px;
}

.dest-select {
  flex: 1 1 200px;
  min-width: 180px;
}

.mode-label {
  font-size: 13px;
  color: var(--mr-text-secondary);
  flex-shrink: 0;
  min-width: 4.5em;
}

.hint-card .hint-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
  color: var(--mr-text-secondary);
  line-height: 1.7;
}

@media (max-width: 720px) {
  .panel-card :deep(.col-path) {
    display: none;
  }
}
</style>
