<script setup lang="ts">
import { computed, ref, watch } from "vue";

import http from "../api/http";
import { errMsg } from "../utils/errMsg";
import { breadcrumbPartsOf, normalizeRelPath, parentRelPath } from "../utils/path";
import { ElMessage } from "element-plus";

type FileEntry = { name: string; path: string; is_dir: boolean };

const props = defineProps<{
  modelValue: boolean;
  /** 打开时初始路径 */
  initialPath?: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [boolean];
  confirm: [path: string];
}>();

const browsePath = ref("");
const entries = ref<FileEntry[]>([]);
const loading = ref(false);

const dirs = computed(() => entries.value.filter((e) => e.is_dir));
const crumbs = computed(() => breadcrumbPartsOf(browsePath.value));

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get<{ path: string; entries: FileEntry[] }>("/files/browse", {
      params: { path: browsePath.value },
    });
    entries.value = data.entries;
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    const next = normalizeRelPath(props.initialPath ?? "");
    if (browsePath.value === next) void load();
    else browsePath.value = next;
  },
);

watch(browsePath, () => {
  if (props.modelValue) void load();
});

function enter(row: FileEntry) {
  if (row.is_dir) browsePath.value = row.path;
}

function goRoot() {
  browsePath.value = "";
}

function goParent() {
  browsePath.value = parentRelPath(browsePath.value);
}

function goIndex(idx: number) {
  browsePath.value = crumbs.value.slice(0, idx + 1).join("/");
}

function confirm() {
  emit("confirm", browsePath.value);
  emit("update:modelValue", false);
}

function close() {
  emit("update:modelValue", false);
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="选择目标目录"
    width="520px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="picker-toolbar">
      <el-breadcrumb separator="/" class="crumb">
        <el-breadcrumb-item>
          <el-link type="primary" @click="goRoot">root</el-link>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-for="(p, idx) in crumbs" :key="idx">
          <el-link type="primary" @click="goIndex(idx)">{{ p }}</el-link>
        </el-breadcrumb-item>
      </el-breadcrumb>
      <el-button text type="primary" :disabled="!browsePath" @click="goParent">上级</el-button>
    </div>
    <el-table
      :data="dirs"
      v-loading="loading"
      height="280"
      size="small"
      row-key="path"
      empty-text="此目录下没有子文件夹"
      @row-dblclick="enter"
    >
      <el-table-column label="文件夹">
        <template #default="{ row }">
          <el-link type="primary" @click="enter(row)">{{ row.name }}/</el-link>
        </template>
      </el-table-column>
    </el-table>
    <p class="hint">当前选中：{{ browsePath || "（挂载根）" }}</p>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" @click="confirm">确定使用此目录</el-button>
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

.hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--mr-text-secondary);
}
</style>
