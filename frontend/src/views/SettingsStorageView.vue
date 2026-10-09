<script setup lang="ts">
import { FolderOpened } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";
import HostDirPickerDialog from "../components/HostDirPickerDialog.vue";
import "../styles/settings-views.css";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { settingsErrMsg } from "../utils/settingsHttp";

const router = useRouter();
const prefs = useBrowsePrefsStore();
const returnTo = computed(() => prefs.returnTo);

function goBackToFiles() {
  const target = prefs.returnTo || "/files";
  prefs.setReturnTo(null);
  void router.push(target);
}

const loading = ref(false);
const saving = ref(false);

const form = reactive({
  mount_path: "",
});

type DestFormRow = { label: string; path: string };
const transferDestinations = ref<DestFormRow[]>([{ label: "", path: "" }]);

const pickerOpen = ref(false);
const pickerInitial = ref("");
const pickerTarget = ref<"mount" | number>("mount");

function openPicker(target: "mount" | number) {
  pickerTarget.value = target;
  pickerInitial.value = target === "mount" ? form.mount_path : transferDestinations.value[target]?.path || "";
  pickerOpen.value = true;
}

function onPicked(path: string) {
  if (pickerTarget.value === "mount") {
    form.mount_path = path;
  } else {
    const row = transferDestinations.value[pickerTarget.value];
    if (row) row.path = path;
  }
}

function addDestRow() {
  transferDestinations.value.push({ label: "", path: "" });
}

function removeDestRow(index: number) {
  transferDestinations.value.splice(index, 1);
  if (transferDestinations.value.length === 0) {
    transferDestinations.value.push({ label: "", path: "" });
  }
}

function normalizeDestinationsForSave(): { label: string; path: string }[] {
  return transferDestinations.value
    .map((r) => ({ label: r.label.trim(), path: r.path.trim() }))
    .filter((r) => r.label && r.path);
}

async function loadSettings() {
  loading.value = true;
  try {
    const { data } = await http.get<{
      mount_path: string;
      transfer_destinations: { id: number; label: string; path: string; ready: boolean }[];
    }>("/settings");
    form.mount_path = data.mount_path;
    const raw = data.transfer_destinations ?? [];
    transferDestinations.value =
      raw.length > 0 ? raw.map((d) => ({ label: d.label, path: d.path })) : [{ label: "", path: "" }];
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    loading.value = false;
  }
}

async function saveStorage() {
  for (const r of transferDestinations.value) {
    const a = r.label.trim();
    const b = r.path.trim();
    if ((a && !b) || (!a && b)) {
      ElMessage.warning("每个传输目标须同时填写显示名称与路径，或清空整行");
      return;
    }
  }
  saving.value = true;
  try {
    await http.patch("/settings", {
      mount_path: form.mount_path,
      transfer_destinations: normalizeDestinationsForSave(),
    });
    ElMessage.success("存储配置已保存");
    await loadSettings();
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadSettings();
});
</script>

<template>
  <div class="settings-page-wrap has-sticky-actionbar" v-loading="loading">
    <div class="page-head mr-page-intro">
      <h1 class="mr-page-title">存储挂载</h1>
      <p class="mr-page-desc">挂载根目录与传输目标路径将作用于文件浏览与「文件传输」功能。</p>
    </div>

    <el-card class="block-card" shadow="never">
      <template #header>
        <div class="card-head mr-card-head">
          <el-icon class="head-ic"><FolderOpened /></el-icon>
          <span>存储挂载</span>
        </div>
      </template>
      <el-form label-position="top" class="nice-form">
        <el-form-item label="挂载根目录">
          <div class="path-pick-row">
            <el-input
              v-model="form.mount_path"
              placeholder="例如容器内 /data 或与 NAS 映射一致的本机路径"
              clearable
            />
            <el-button @click="openPicker('mount')">浏览目录</el-button>
          </div>
          <div class="hint">可浏览服务端（容器）内已有文件夹并选择；须与实际映射到 NAS 的路径一致，保存后立即生效。</div>
        </el-form-item>
        <el-form-item label="传输目标（可多选）">
          <div class="dest-list">
            <div v-for="(row, idx) in transferDestinations" :key="idx" class="dest-row">
              <el-input v-model="row.label" placeholder="显示名称（如：电影）" clearable class="dest-label" />
              <el-input
                v-model="row.path"
                placeholder="服务端绝对路径，例如 /backup/movies"
                clearable
                class="dest-path"
              />
              <el-button @click="openPicker(idx)">浏览</el-button>
              <el-button type="danger" plain :disabled="transferDestinations.length <= 1" @click="removeDestRow(idx)">
                删除
              </el-button>
            </div>
            <el-button type="primary" plain class="add-dest" @click="addDestRow">添加目标</el-button>
          </div>
          <div class="hint">
            用于「文件传输」：在传输页选择其中一个目标；路径须为服务端绝对路径，保存时会规范化；目录须已存在且可访问时该目标才显示为可用（ready）。
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="mr-sticky-actionbar">
      <div class="mr-sticky-actionbar__inner">
        <el-button v-if="returnTo" size="large" @click="goBackToFiles">返回文件页</el-button>
        <el-button type="primary" size="large" :loading="saving" class="save-btn" @click="saveStorage">
          保存存储配置
        </el-button>
      </div>
    </div>

    <HostDirPickerDialog v-model="pickerOpen" :initial-path="pickerInitial" @confirm="onPicked" />
  </div>
</template>
