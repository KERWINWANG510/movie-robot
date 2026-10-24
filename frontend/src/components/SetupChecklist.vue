<script setup lang="ts">
import { ArrowRight, Check } from "@element-plus/icons-vue";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { errMsg } from "../utils/errMsg";

type ChecklistState = {
  mount_ready: boolean;
  mount_path: string;
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
  mount_path: "",
  has_ready_dest: false,
  ai_ready: false,
});

const allDone = computed(() => {
  if (!state.value.mount_ready) return false;
  if (props.context === "transfer") return state.value.has_ready_dest;
  return state.value.ai_ready;
});

/** 未完成且未关闭时用警告样式；完成时仍展示就绪条（对齐 Stitch） */
const showStrip = computed(() => !loading.value && (!prefs.checklistDismissed || allDone.value));

async function load() {
  loading.value = true;
  try {
    const { data } = await http.get<{
      mount_ready: boolean;
      mount_path: string;
      transfer_destinations: { ready: boolean }[];
      api_key_saved_in_db: boolean;
      openai_model: string;
    }>("/settings");
    state.value = {
      mount_ready: data.mount_ready,
      mount_path: (data.mount_path || "").trim(),
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

function goConfig() {
  if (props.context === "transfer") goStorage();
  else if (!state.value.mount_ready) goStorage();
  else goAi();
}

function dismiss() {
  prefs.checklistDismissed = true;
}

const mountLabel = computed(() => {
  const p = state.value.mount_path;
  if (state.value.mount_ready) {
    return p ? `媒体挂载点就绪 (${p})` : "媒体挂载点就绪";
  }
  return "媒体挂载点未配置";
});

const aiLabel = computed(() =>
  state.value.ai_ready ? "AI 识别大模型配置有效" : "AI 密钥 / 模型待配置",
);

const destLabel = computed(() =>
  state.value.has_ready_dest ? "传输目标已就绪" : "传输目标待配置",
);

onMounted(() => {
  void load();
});

defineExpose({ reload: load });
</script>

<template>
  <div v-if="showStrip" class="status-strip" :class="{ warn: !allDone }">
    <div class="strip-items">
      <button
        type="button"
        class="strip-item"
        :class="{ ok: state.mount_ready, bad: !state.mount_ready }"
        @click="goStorage"
      >
        <el-icon v-if="state.mount_ready" class="ic"><Check /></el-icon>
        <span v-else class="dot warn-dot" />
        <span class="label">{{ mountLabel }}</span>
      </button>

      <button
        v-if="context === 'transfer'"
        type="button"
        class="strip-item"
        :class="{ ok: state.has_ready_dest, bad: !state.has_ready_dest }"
        @click="goStorage"
      >
        <el-icon v-if="state.has_ready_dest" class="ic"><Check /></el-icon>
        <span v-else class="dot warn-dot" />
        <span class="label">{{ destLabel }}</span>
      </button>

      <button
        v-else
        type="button"
        class="strip-item"
        :class="{ ok: state.ai_ready, bad: !state.ai_ready }"
        @click="goAi"
      >
        <el-icon v-if="state.ai_ready" class="ic"><Check /></el-icon>
        <span v-else class="dot warn-dot" />
        <span class="label">{{ aiLabel }}</span>
      </button>
    </div>

    <div class="strip-actions">
      <button v-if="!allDone" type="button" class="strip-link" @click="goConfig">
        <span>配置详情</span>
        <el-icon><ArrowRight /></el-icon>
      </button>
      <button v-if="!allDone" type="button" class="strip-dismiss" @click="dismiss">不再提示</button>
    </div>
  </div>
</template>

<style scoped>
.status-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
  padding: 10px 16px;
  margin-bottom: 16px;
  border-radius: 8px;
  background: var(--surface-low, #1b1b1d);
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-family: var(--mr-font-mono);
  font-size: 12px;
}

.strip-items {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
  min-width: 0;
}

.strip-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--mr-text-secondary);
  font: inherit;
  cursor: pointer;
  text-align: left;
}

.strip-item.ok {
  color: var(--el-color-success);
}

.strip-item.bad {
  color: var(--el-color-warning);
}

.strip-item .ic {
  font-size: 14px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.warn-dot {
  background: var(--el-color-warning);
}

.label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: min(420px, 70vw);
}

.strip-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.strip-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--el-color-primary);
  font-family: var(--mr-font-sans);
  font-size: 13px;
  cursor: pointer;
}

.strip-link:hover {
  text-decoration: underline;
}

.strip-dismiss {
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--mr-text-muted);
  font-family: var(--mr-font-sans);
  font-size: 12px;
  cursor: pointer;
}

.strip-dismiss:hover {
  color: var(--mr-text-secondary);
}

@media (max-width: 720px) {
  .status-strip {
    padding: 10px 12px;
  }
  .label {
    white-space: normal;
    max-width: none;
  }
}
</style>
