<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessage } from "element-plus";

import http from "../api/http";
import { settingsErrMsg } from "../utils/settingsHttp";

type HostDirEntry = { name: string; path: string };

const props = defineProps<{
  modelValue: boolean;
  /** 打开时尽量定位到该绝对路径 */
  initialPath?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [boolean];
  confirm: [path: string];
}>();

const currentPath = ref("");
const entries = ref<HostDirEntry[]>([]);
const loading = ref(false);
const filterText = ref("");

const filtered = computed(() => {
  const q = filterText.value.trim().toLowerCase();
  if (!q) return entries.value;
  return entries.value.filter((e) => e.name.toLowerCase().includes(q) || e.path.toLowerCase().includes(q));
});

const crumbs = computed(() => {
  const p = currentPath.value.replace(/\\/g, "/").replace(/\/+$/, "");
  if (!p) return [] as { label: string; path: string }[];
  if (/^[A-Za-z]:$/.test(p) || /^[A-Za-z]:\/$/.test(currentPath.value)) {
    return [{ label: currentPath.value, path: currentPath.value }];
  }
  const parts = p.split("/").filter(Boolean);
  const out: { label: string; path: string }[] = [];
  if (p.startsWith("/")) {
    let acc = "";
    for (const part of parts) {
      acc += `/${part}`;
      out.push({ label: part, path: acc });
    }
    return out;
  }
  let acc = "";
  for (const part of parts) {
    acc = acc ? `${acc}/${part}` : part;
    out.push({ label: part, path: acc.replace(/\//g, "\\") });
  }
  return out;
});

async function load(path: string, silent = false): Promise<boolean> {
  loading.value = true;
  try {
    const { data } = await http.get<{ path: string; entries: HostDirEntry[] }>("/settings/host-dirs", {
      params: { path },
    });
    currentPath.value = data.path ?? "";
    entries.value = data.entries ?? [];
    filterText.value = "";
    return true;
  } catch (e: unknown) {
    if (!silent) ElMessage.error(settingsErrMsg(e));
    return false;
  } finally {
    loading.value = false;
  }
}

async function openAt(start: string) {
  const raw = (start || "").trim();
  if (!raw) {
    await load("");
    return;
  }
  const ok = await load(raw, true);
  if (!ok) await load("");
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    void openAt(props.initialPath ?? "");
  },
);

function enter(row: HostDirEntry) {
  void load(row.path);
}

function goRoot() {
  void load("");
}

function goParent() {
  const p = currentPath.value;
  if (!p) return;
  const norm = p.replace(/\\/g, "/").replace(/\/+$/, "");
  if (norm === "" || norm === "/" || /^[A-Za-z]:$/.test(norm) || /^[A-Za-z]:\/$/.test(p)) {
    void load("");
    return;
  }
  const idx = Math.max(norm.lastIndexOf("/"), norm.lastIndexOf("\\"));
  const parent = idx <= 0 ? (norm.startsWith("/") ? "/" : "") : norm.slice(0, idx);
  void load(parent || "");
}

function confirm() {
  if (!currentPath.value) {
    ElMessage.warning("请先进入一个具体目录再确认");
    return;
  }
  emit("confirm", currentPath.value);
  emit("update:modelValue", false);
}

function close() {
  emit("update:modelValue", false);
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="选择系统目录"
    width="560px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="picker-toolbar">
      <el-breadcrumb separator="/" class="crumb">
        <el-breadcrumb-item>
          <el-link type="primary" @click="goRoot">本机</el-link>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-for="(c, idx) in crumbs" :key="idx">
          <el-link type="primary" @click="load(c.path)">{{ c.label }}</el-link>
        </el-breadcrumb-item>
      </el-breadcrumb>
      <el-button text type="primary" :disabled="!currentPath" @click="goParent">上级</el-button>
    </div>
    <el-input
      v-model="filterText"
      clearable
      placeholder="筛选当前层文件夹名称…"
      class="picker-filter"
    />
    <el-table
      :data="filtered"
      v-loading="loading"
      height="280"
      size="small"
      row-key="path"
      empty-text="没有可进入的文件夹"
      highlight-current-row
      @row-click="enter"
    >
      <el-table-column label="文件夹">
        <template #default="{ row }">
          <el-link type="primary">{{ row.name }}/</el-link>
        </template>
      </el-table-column>
    </el-table>
    <p class="hint">当前选中：{{ currentPath || "（请进入一个目录）" }} · 单击进入子目录</p>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :disabled="!currentPath" @click="confirm">确定使用此目录</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.picker-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.crumb {
  flex: 1;
  min-width: 0;
  font-size: 13px;
}

.picker-filter {
  margin-bottom: 10px;
}

.hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--mr-text-secondary);
}
</style>
