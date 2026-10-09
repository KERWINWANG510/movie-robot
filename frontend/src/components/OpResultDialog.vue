<script setup lang="ts">
import { computed } from "vue";

export type OpResultItem = {
  key: string;
  source: string;
  dest?: string;
  ok: boolean;
  message: string | null;
};

const props = defineProps<{
  modelValue: boolean;
  title?: string;
  results: OpResultItem[];
  /** 是否展示「重试失败项」 */
  canRetry?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [boolean];
  retry: [failed: OpResultItem[]];
}>();

const failed = computed(() => props.results.filter((r) => !r.ok));
const okCount = computed(() => props.results.filter((r) => r.ok).length);

function close() {
  emit("update:modelValue", false);
}

function onRetry() {
  emit("retry", failed.value);
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title || '操作结果'"
    width="640px"
    class="op-result-dialog"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <p class="summary">
      成功 {{ okCount }} 项，失败 {{ failed.length }} 项
    </p>
    <el-table :data="results" size="small" max-height="360" row-key="key">
      <el-table-column label="状态" width="72">
        <template #default="{ row }">
          <el-tag :type="row.ok ? 'success' : 'danger'" size="small">
            {{ row.ok ? "成功" : "失败" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="源" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">{{ row.source }}</template>
      </el-table-column>
      <el-table-column v-if="results.some((r) => r.dest)" label="目标" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.dest || "—" }}</template>
      </el-table-column>
      <el-table-column label="说明" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span :class="{ 'is-err': !row.ok }">{{ row.message || (row.ok ? "完成" : "失败") }}</span>
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <el-button @click="close">关闭</el-button>
      <el-button v-if="canRetry && failed.length" type="primary" @click="onRetry">
        重试失败项（{{ failed.length }}）
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.summary {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--mr-text-secondary);
}

.is-err {
  color: var(--el-color-danger);
}
</style>
