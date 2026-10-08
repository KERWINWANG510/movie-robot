<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { errMsg } from "../utils/errMsg";

type ChecklistState = {
  mount_ready: boolean;
  has_ready_dest: boolean;
  ai_ready: boolean;
};

const props = defineProps<{
  /** rename 更关心 AI；transfer 更关心目标 */
  context?: "rename" | "merge" | "transfer";
}>();

const router = useRouter();
const prefs = useBrowsePrefsStore();

const loading = ref(true);
const state = ref<ChecklistState>({
  mount_ready: false,
  has_ready_dest: false,
  ai_ready: false,
});

const allDone = computed(() => {
  if (!state.value.mount_ready) return false;
  if (props.context === "transfer") return state.value.has_ready_dest;
  return state.value.ai_ready;
});

const show = computed(() => !loading.value && !prefs.checklistDismissed && !allDone.value);

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get<{
      mount_ready: boolean;
      transfer_destinations: { ready: boolean }[];
      api_key_saved_in_db: boolean;
      openai_model: string;
    }>("/settings");
    state.value = {
      mount_ready: data.mount_ready,
      has_ready_dest: (data.transfer_destinations ?? []).some((d) => d.ready),
      ai_ready: Boolean(data.api_key_saved_in_db && (data.openai_model || "").trim()),
    };
  } catch (e: unknown) {
    console.warn(errMsg(e));
  } finally {
    loading.value = false;
  }
}

function goStorage() {
  prefs.setReturnTo(router.currentRoute.value.fullPath);
  router.push({ name: "settings-storage" });
}

function goAi() {
  prefs.setReturnTo(router.currentRoute.value.fullPath);
  router.push({ name: "settings-ai" });
}

function dismiss() {
  prefs.checklistDismissed = true;
}

onMounted(() => {
  void load();
});

defineExpose({ reload: load });
</script>

<template>
  <el-alert v-if="show" type="info" :closable="false" class="checklist" show-icon>
    <template #title>配置检查清单</template>
    <ul class="list">
      <li :class="{ done: state.mount_ready }">
        <span>挂载根目录</span>
        <el-button v-if="!state.mount_ready" link type="primary" @click="goStorage">去配置</el-button>
        <span v-else class="ok">已完成</span>
      </li>
      <li v-if="context === 'transfer'" :class="{ done: state.has_ready_dest }">
        <span>传输目标（至少一个可用）</span>
        <el-button v-if="!state.has_ready_dest" link type="primary" @click="goStorage">去配置</el-button>
        <span v-else class="ok">已完成</span>
      </li>
      <li v-if="context !== 'transfer'" :class="{ done: state.ai_ready }">
        <span>AI 密钥与模型</span>
        <el-button v-if="!state.ai_ready" link type="primary" @click="goAi">去配置</el-button>
        <span v-else class="ok">已完成</span>
      </li>
    </ul>
    <div class="actions">
      <el-button size="small" text @click="dismiss">不再提示</el-button>
    </div>
  </el-alert>
</template>

<style scoped>
.checklist {
  margin-bottom: 12px;
  border-radius: var(--mr-radius-md);
}

.list {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0;
  font-size: 13px;
}

.list li.done {
  color: var(--mr-text-muted);
}

.ok {
  font-size: 12px;
  color: var(--el-color-success);
}

.actions {
  margin-top: 6px;
}
</style>
