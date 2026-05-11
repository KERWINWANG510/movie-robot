<script setup lang="ts">
import { Setting, Upload } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";

type FileEntry = { name: string; path: string; is_dir: boolean };

type BrowseResponse = {
  path: string;
  entries: FileEntry[];
};

type TransferDest = { id: number; label: string; path: string; ready: boolean };

function errMsg(e: unknown): string {
  if (typeof e === "object" && e !== null && "response" in e) {
    const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => JSON.stringify(x)).join("; ");
  }
  return "请求失败";
}

const router = useRouter();

const mountReady = ref(false);
const transferDestinations = ref<TransferDest[]>([]);
const selectedDestinationId = ref<number | null>(null);
const setupLoading = ref(true);

const currentPath = ref("");
const entries = ref<FileEntry[]>([]);
const browseLoading = ref(false);

const selectedPaths = ref<string[]>([]);
const transferMode = ref<"copy" | "move">("copy");
const transferLoading = ref(false);

const breadcrumbParts = computed(() => {
  if (!currentPath.value) return [];
  return currentPath.value.split("/").filter(Boolean);
});

const needMountSetup = computed(() => !mountReady.value);
const hasAnyDestination = computed(() => transferDestinations.value.length > 0);
const hasReadyDestination = computed(() => transferDestinations.value.some((d) => d.ready));

const selectedDest = computed(() => transferDestinations.value.find((d) => d.id === selectedDestinationId.value) ?? null);

const transferAllowed = computed(
  () => Boolean(selectedDest.value?.ready && selectedPaths.value.length > 0),
);

async function refreshSettingsAndBrowse() {
  setupLoading.value = true;
  try {
    const { data } = await http.get<{ mount_ready: boolean; transfer_destinations: TransferDest[] }>("/settings");
    mountReady.value = data.mount_ready;
    transferDestinations.value = data.transfer_destinations ?? [];
    const firstReady = transferDestinations.value.find((d) => d.ready);
    if (firstReady) {
      selectedDestinationId.value = firstReady.id;
    } else {
      selectedDestinationId.value = transferDestinations.value[0]?.id ?? null;
    }
    currentPath.value = "";
    if (data.mount_ready) {
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
  } catch (e: unknown) {
    const msg = errMsg(e);
    ElMessage.error(msg);
    if (msg.includes("不存在")) {
      currentPath.value = "";
    }
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
  selectedPaths.value = rows.map((r) => r.path);
}

function goSettings() {
  router.push({ name: "settings-storage" });
}

watch(currentPath, () => {
  if (mountReady.value) {
    loadBrowse();
  }
});

async function runTransfer() {
  if (selectedPaths.value.length === 0) {
    ElMessage.warning("请先勾选要传输的文件或文件夹");
    return;
  }
  if (!selectedDestinationId.value || !selectedDest.value?.ready) {
    ElMessage.warning("请选择一个可用的传输目标（路径须已存在且为目录）");
    return;
  }
  const verb = transferMode.value === "copy" ? "复制" : "移动";
  const label = selectedDest.value.label;
  try {
    await ElMessageBox.confirm(
      `将把所选 ${selectedPaths.value.length} 项${verb}到「${label}」。目标侧重名会自动加 _1、_2 等后缀；目录整体传输时若重名则使用 foo_1 形式。是否继续？`,
      `文件传输（${verb}）`,
      { type: "warning", confirmButtonText: "开始传输", cancelButtonText: "取消" },
    );
  } catch {
    return;
  }
  transferLoading.value = true;
  try {
    const { data } = await http.post<{
      results: { source_path: string; dest_path: string; ok: boolean; message: string | null }[];
      ok_count: number;
      failed_count: number;
    }>("/files/transfer", {
      paths: selectedPaths.value,
      mode: transferMode.value,
      destination_id: selectedDestinationId.value,
    });
    if (data.failed_count === 0) {
      ElMessage.success(`已传输 ${data.ok_count} 项`);
    } else {
      ElMessage.warning(`完成：成功 ${data.ok_count}，失败 ${data.failed_count}`);
    }
    selectedPaths.value = [];
    await loadBrowse();
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    transferLoading.value = false;
  }
}

refreshSettingsAndBrowse();
</script>

<template>
  <div class="transfer-page" v-loading="setupLoading">
    <template v-if="mountReady">
      <div class="mr-page-intro">
        <h2 class="mr-page-title">文件传输</h2>
        <p class="mr-page-desc">
          在挂载目录中多选文件或文件夹，选择传输目标后复制或剪切到对应目录（可为挂载外的绝对路径）。名称冲突时自动加序号。
        </p>
      </div>

      <el-alert v-if="!hasAnyDestination" type="warning" :closable="false" class="mb-alert" show-icon>
        <template #title>尚未配置传输目标</template>
        请先在「系统配置 → 存储挂载」中添加至少一个传输目标（显示名称 + 服务端路径），保存后即可在此选择。
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
        已配置的目录在服务端不存在或不可访问时不可用。请检查挂载、权限与路径是否正确，或与挂载根使用相同的路径写法。
        <div class="alert-actions">
          <el-button type="primary" size="small" @click="goSettings">前往系统配置</el-button>
        </div>
      </el-alert>

      <el-row :gutter="18">
        <el-col :xs="24" :lg="16">
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
              :data="entries"
              v-loading="browseLoading"
              row-key="path"
              height="360"
              class="file-table"
              @selection-change="onSelectionChange"
            >
              <el-table-column type="selection" width="48" />
              <el-table-column label="名称" min-width="160">
                <template #default="{ row }">
                  <el-link v-if="row.is_dir" type="primary" @click="enterDir(row)">{{ row.name }}/</el-link>
                  <span v-else>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="路径" prop="path" min-width="220" show-overflow-tooltip />
            </el-table>

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
              <el-radio-group v-model="transferMode">
                <el-radio-button value="copy">复制</el-radio-button>
                <el-radio-button value="move">剪切</el-radio-button>
              </el-radio-group>
            </div>
            <div class="mr-actions">
              <el-button
                type="primary"
                :loading="transferLoading"
                :disabled="!transferAllowed"
                @click="runTransfer"
              >
                <el-icon class="btn-ic"><Upload /></el-icon>
                传输到所选目标
              </el-button>
            </div>
            <p class="mr-tips">剪切会移动原路径；若目标已存在同名文件或文件夹，将自动使用 _1、_2 等后缀避免覆盖。</p>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="panel-card hint-card">
            <template #header>
              <div class="mr-card-head"><span>说明</span></div>
            </template>
            <ul class="hint-list">
              <li>传输目标在「系统配置 → 存储挂载」中维护，可配置多个；须为服务端可访问的绝对路径。</li>
              <li>不能选择互为父子关系的路径（例如不要同时勾选文件夹与其中的项）。</li>
              <li>传输目标不能与挂载根相同，也不能落在所选源路径内部。</li>
            </ul>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <div v-else-if="!setupLoading && needMountSetup" class="mr-setup-wrap">
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
.transfer-page {
  max-width: 1280px;
  margin: 0 auto;
  min-height: 240px;
}

.mb-alert {
  margin-bottom: 18px;
  border-radius: var(--mr-radius-md);
}

.mb-alert :deep(.el-alert__title) {
  font-weight: 600;
}

.alert-actions {
  margin-top: 12px;
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

.dest-select-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.dest-select {
  flex: 1 1 220px;
  min-width: 200px;
}

.mode-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.mode-label {
  font-size: 14px;
  color: var(--mr-text-secondary);
}

.file-table {
  width: 100%;
}

.hint-card .hint-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
  color: var(--mr-text-secondary);
  line-height: 1.7;
}

@media (max-width: 992px) {
  .file-table {
    height: auto !important;
  }
}
</style>
