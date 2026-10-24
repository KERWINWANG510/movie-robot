<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const tabs = [
  { name: "settings-storage" as const, label: "存储挂载" },
  { name: "settings-ai" as const, label: "AI 服务" },
  { name: "settings-media" as const, label: "影视数据源" },
  { name: "settings-open-api" as const, label: "开放接口" },
];

const active = computed(() => String(route.name ?? ""));

function go(name: (typeof tabs)[number]["name"]) {
  if (name === active.value) return;
  void router.push({ name });
}
</script>

<template>
  <div class="settings-subnav" role="tablist">
    <button
      v-for="t in tabs"
      :key="t.name"
      type="button"
      class="settings-subnav-btn"
      :class="{ active: active === t.name }"
      role="tab"
      :aria-selected="active === t.name"
      @click="go(t.name)"
    >
      <span v-if="active === t.name" class="dot" />
      {{ t.label }}
    </button>
  </div>
</template>

<style scoped>
.settings-subnav {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 2px;
  padding: 4px;
  margin-bottom: 16px;
  border-radius: 12px;
  background: var(--surface-low, #1b1b1d);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.settings-subnav-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 7px 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--mr-text-secondary);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}

.settings-subnav-btn:hover {
  color: var(--mr-text);
}

.settings-subnav-btn.active {
  font-weight: 600;
  color: var(--mr-text);
  background: var(--surface-high, #2b2b2e);
  border-color: rgba(255, 255, 255, 0.1);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-primary);
}

@media (max-width: 720px) {
  .settings-subnav {
    width: 100%;
  }
  .settings-subnav-btn {
    flex: 1 1 auto;
    justify-content: center;
    padding: 8px 10px;
    font-size: 12px;
  }
}
</style>
