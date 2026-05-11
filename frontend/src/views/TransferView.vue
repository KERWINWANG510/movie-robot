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
const transferTargetReady = ref(false);
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
const needTransferSetup = computed(() => mountReady.value && !transferTargetReady.value);

async function refreshSettingsAndBrowse() {
  setupLoading.value = true;
  try {
    const { data } = await http.get<{ mount_ready: boolean; transfer_target_ready: boolean }>("/settings");
    mountReady.value = data.mount_ready;
    transferTargetReady.value = data.transfer_target_ready;
    currentPath.value = "";
    if (data.mount_ready && data.transfer_target_ready) {
      await loadBrowse();
    } else {
      entries.value = [];
      selectedPaths.value = [];
    }
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
    mountReady.value = false;
    transferTargetReady.value = false;
  } finally {
    setupLoading.value = false;
  }
}

async function loadBrowse() {
  if (!mountReady.value || !transferTargetReady.value) return;
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
  router.push({ name: "settings" });
}

watch(currentPath, () => {
  if (mountReady.value && transferTargetReady.value) {
    loadBrowse();
  }
});

async function runTransfer() {
  if (selectedPaths.value.length === 0) {
    ElMessage.warning("请先勾选要传输的文件或文件夹");
    return;
  }
  const verb = transferMode.value === "copy" ? "复制" : "移动";
  try {
    await ElMessageBox.confirm(
      `将把所选 ${selectedPaths.value.length} 项${verb}到系统配置中的「传输目标目录」。目标侧重名会自动加 _1、_2 等后缀；目录整体传输时若重名则使用 foo_1 形式。是否继续？`,
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
    <template v-if="mountReady && transferTargetReady">
      <div class="page-intro">
        <h2 class="page-title">文件传输</h2>
        <p class="page-desc">
          在挂载目录中多选文件或文件夹，复制或剪切到「系统配置」中设置的传输目标目录（可为挂载外的绝对路径）。名称冲突时自动加序号。
        </p>
      </div>
      <el-row :gutter="16">
        <el-col :xs="24" :lg="16">
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
              <el-table-column type="selection" width="48" />
              <el-table-column label="名称" min-width="160">
                <template #default="{ row }">
                  <el-link v-if="row.is_dir" type="primary" @click="enterDir(row)">{{ row.name }}/</el-link>
                  <span v-else>{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="路径" prop="path" min-width="220" show-overflow-tooltip />
            </el-table>

            <div class="mode-row">
              <span class="mode-label">传输方式</span>
              <el-radio-group v-model="transferMode">
                <el-radio-button value="copy">复制</el-radio-button>
                <el-radio-button value="move">剪切</el-radio-button>
              </el-radio-group>
            </div>
            <div class="actions">
              <el-button type="primary" :loading="transferLoading" :disabled="!selectedPaths.length" @click="runTransfer">
                <el-icon class="btn-ic"><Upload /></el-icon>
                传输到目标目录
              </el-button>
            </div>
            <p class="tips">剪切会移动原路径；若目标已存在同名文件或文件夹，将自动使用 _1、_2 等后缀避免覆盖。</p>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="8">
          <el-card shadow="never" class="hint-card">
            <template #header>
              <span>说明</span>
            </template>
            <ul class="hint-list">
              <li>传输目标在「系统配置 → 传输目标目录」中维护，须为服务端可访问的目录路径。</li>
              <li>不能选择互为父子关系的路径（例如不要同时勾选文件夹与其中的项）。</li>
              <li>传输目标不能与挂载根相同，也不能落在所选源路径内部。</li>
            </ul>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <div v-else-if="!setupLoading && needMountSetup" class="setup-wrap">
      <el-card class="setup-card" shadow="hover">
        <div class="setup-inner">
          <h2 class="page-title">请先配置挂载目录</h2>
          <p class="setup-desc">
            当前还没有可用的挂载根路径（路径不存在或不是文件夹）。请在系统配置中填写并保存「挂载根目录」，确保该路径在服务端可访问。
          </p>
          <el-button type="primary" size="large" @click="goSettings">
            <el-icon class="btn-ic"><Setting /></el-icon>
            前往系统配置
          </el-button>
        </div>
      </el-card>
    </div>

    <div v-else-if="!setupLoading && needTransferSetup" class="setup-wrap">
      <el-card class="setup-card" shadow="hover">
        <div class="setup-inner">
          <h2 class="page-title">请配置传输目标目录</h2>
          <p class="setup-desc">
            文件传输需要有效的「传输目标目录」（服务端绝对路径，且为已存在的文件夹）。请在系统配置中填写并保存；保存后若路径可访问，即可在本页浏览挂载目录并执行传输。
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

.page-intro {
  margin-bottom: 16px;
}

.page-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: #909399;
  line-height: 1.5;
}

.setup-wrap {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

.setup-card {
  width: 100%;
  max-width: 520px;
  border-radius: 14px;
}

.setup-inner {
  padding: 12px 8px 8px;
  text-align: center;
}

.setup-desc {
  margin: 0 0 24px;
  font-size: 14px;
  color: #606266;
  line-height: 1.65;
  text-align: left;
}

.btn-ic {
  margin-right: 6px;
  vertical-align: middle;
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

.mode-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.mode-label {
  font-size: 14px;
  color: #606266;
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

.file-table {
  width: 100%;
}

.hint-card .hint-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}

@media (max-width: 992px) {
  .file-table {
    height: auto !important;
  }
}
</style>
