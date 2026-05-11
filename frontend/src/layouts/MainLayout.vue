<script setup lang="ts">
import { CopyDocument, EditPen, Menu as IconMenu, Setting, Upload } from "@element-plus/icons-vue";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const drawerVisible = ref(false);

/** 侧栏子菜单 index，须与模板中 el-sub-menu 的 index 一致 */
const SETTINGS_SUBMENU_INDEX = "settings-submenu";

type TopNavName = "rename" | "folder-merge" | "transfer";
type MenuLeafIndex = TopNavName | "settings-storage" | "settings-ai";

const isSettingsBranch = computed(
  () => route.name === "settings-storage" || route.name === "settings-ai",
);

/** 跨越「是否处于系统配置下」时重挂菜单，以便 default-openeds 在首次进入配置页时展开子菜单 */
const sideMenuInstanceKey = computed(() => (isSettingsBranch.value ? "nav-settings" : "nav-top"));

const submenuDefaultOpeneds = computed(() => (isSettingsBranch.value ? [SETTINGS_SUBMENU_INDEX] : []));

function goTop(name: TopNavName) {
  router.push({ name });
}

function goSettingsChild(name: "settings-storage" | "settings-ai") {
  router.push({ name });
}

function onDrawerSelect(index: string) {
  const leaf = index as MenuLeafIndex;
  if (leaf === "rename" || leaf === "folder-merge" || leaf === "transfer") {
    router.push({ name: leaf });
    drawerVisible.value = false;
    return;
  }
  if (leaf === "settings-storage" || leaf === "settings-ai") {
    router.push({ name: leaf });
    drawerVisible.value = false;
  }
}

async function logout() {
  await auth.logout();
  await router.replace({ name: "login" });
}

const activeMenu = computed(() => {
  if (route.name === "settings-storage") return "settings-storage";
  if (route.name === "settings-ai") return "settings-ai";
  if (route.name === "transfer") return "transfer";
  if (route.name === "folder-merge") return "folder-merge";
  return "rename";
});
</script>

<template>
  <div class="app-shell">
    <header class="top-bar">
      <div class="top-left">
        <el-button class="menu-btn" text circle @click="drawerVisible = true">
          <el-icon :size="22"><IconMenu /></el-icon>
        </el-button>
        <router-link to="/" class="logo">
          <span class="logo-mark">MR</span>
          <span class="logo-text">智能文件重命名</span>
        </router-link>
      </div>
      <div class="top-right">
        <span v-if="auth.user" class="who">{{ auth.user.username }}</span>
        <el-button type="primary" plain size="small" @click="logout">退出</el-button>
      </div>
    </header>

    <div class="body">
      <aside class="side-desktop" aria-label="主导航">
        <el-menu
          :key="sideMenuInstanceKey"
          :default-active="activeMenu"
          :default-openeds="submenuDefaultOpeneds"
          class="side-menu"
        >
          <el-menu-item index="rename" @click="goTop('rename')">
            <el-icon><EditPen /></el-icon>
            <span>文件重命名</span>
          </el-menu-item>
          <el-menu-item index="folder-merge" @click="goTop('folder-merge')">
            <el-icon><CopyDocument /></el-icon>
            <span>文件夹合并</span>
          </el-menu-item>
          <el-menu-item index="transfer" @click="goTop('transfer')">
            <el-icon><Upload /></el-icon>
            <span>文件传输</span>
          </el-menu-item>
          <el-sub-menu :index="SETTINGS_SUBMENU_INDEX">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统配置</span>
            </template>
            <el-menu-item index="settings-storage" @click="goSettingsChild('settings-storage')">存储挂载</el-menu-item>
            <el-menu-item index="settings-ai" @click="goSettingsChild('settings-ai')">AI 服务</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </aside>

      <main class="main-pane">
        <router-view />
      </main>
    </div>

    <el-drawer v-model="drawerVisible" direction="ltr" size="280px" title="导航菜单" class="nav-drawer">
      <el-menu
        :key="sideMenuInstanceKey"
        :default-active="activeMenu"
        :default-openeds="submenuDefaultOpeneds"
        @select="onDrawerSelect"
      >
        <el-menu-item index="rename">
          <el-icon><EditPen /></el-icon>
          <span>文件重命名</span>
        </el-menu-item>
        <el-menu-item index="folder-merge">
          <el-icon><CopyDocument /></el-icon>
          <span>文件夹合并</span>
        </el-menu-item>
        <el-menu-item index="transfer">
          <el-icon><Upload /></el-icon>
          <span>文件传输</span>
        </el-menu-item>
        <el-sub-menu :index="SETTINGS_SUBMENU_INDEX">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统配置</span>
          </template>
          <el-menu-item index="settings-storage">存储挂载</el-menu-item>
          <el-menu-item index="settings-ai">AI 服务</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-drawer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(58, 124, 232, 0.09), transparent 55%),
    radial-gradient(900px 480px at 100% 0%, rgba(103, 194, 58, 0.06), transparent 50%),
    linear-gradient(165deg, var(--mr-bg-page) 0%, #e8edf4 48%, var(--mr-bg-page) 100%);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px 12px 10px;
  background: color-mix(in srgb, var(--mr-bg-elevated) 88%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--mr-border-soft);
  box-shadow: var(--mr-shadow-nav);
  position: sticky;
  top: 0;
  z-index: 20;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.menu-btn {
  display: none;
  color: var(--mr-text-secondary);
  transition: color var(--mr-transition-fast), background-color var(--mr-transition-fast);
}

.menu-btn:hover {
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9) !important;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
  min-width: 0;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 11px;
  background: linear-gradient(135deg, var(--el-color-primary) 0%, #4f8ff0 45%, #5cb87a 100%);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: -0.5px;
  flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(58, 124, 232, 0.35);
}

.logo-text {
  font-weight: 600;
  font-size: 16px;
  color: var(--mr-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.02em;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.who {
  font-size: 13px;
  color: var(--mr-text-secondary);
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--el-fill-color-light);
}

.body {
  flex: 1;
  display: flex;
  max-width: 1320px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.side-desktop {
  width: 228px;
  flex-shrink: 0;
  padding: 20px 0 20px 14px;
}

.side-menu {
  border-radius: var(--mr-radius-md);
  border: 1px solid var(--mr-border-soft);
  overflow: hidden;
  box-shadow: var(--mr-shadow-sm);
  --el-menu-bg-color: var(--mr-bg-elevated);
  padding: 6px;
}

.side-menu :deep(.el-menu-item) {
  border-radius: var(--mr-radius-sm);
  margin: 2px 0;
  height: 44px;
  line-height: 44px;
  transition:
    background-color var(--mr-transition-fast),
    color var(--mr-transition-fast),
    transform var(--mr-transition-fast);
}

.side-menu :deep(.el-menu-item:hover) {
  background-color: var(--el-color-primary-light-9) !important;
}

.side-menu :deep(.el-menu-item.is-active) {
  color: var(--el-color-primary) !important;
  background: linear-gradient(90deg, var(--el-color-primary-light-9), var(--el-color-primary-light-8)) !important;
  font-weight: 600;
}

.side-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
}

.side-menu :deep(.el-sub-menu__title) {
  border-radius: var(--mr-radius-sm);
  margin: 2px 0;
  height: 44px;
  line-height: 44px;
  transition:
    background-color var(--mr-transition-fast),
    color var(--mr-transition-fast);
}

.side-menu :deep(.el-sub-menu__title:hover) {
  background-color: var(--el-color-primary-light-9) !important;
}

.side-menu :deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
  padding-left: 44px !important;
}

.side-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--el-color-primary);
  font-weight: 600;
}

.nav-drawer :deep(.el-sub-menu__title) {
  border-radius: var(--mr-radius-sm);
  margin: 4px 8px;
  width: auto;
  transition:
    background-color var(--mr-transition-fast),
    color var(--mr-transition-fast);
}

.nav-drawer :deep(.el-sub-menu .el-menu-item) {
  margin: 2px 8px 2px 16px;
  min-width: 0;
}

.nav-drawer :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--el-color-primary);
  font-weight: 600;
}

.main-pane {
  flex: 1;
  min-width: 0;
  padding: 20px 20px 28px;
}

.nav-drawer :deep(.el-menu) {
  border-right: none;
  padding: 4px 0;
  background: transparent;
}

.nav-drawer :deep(.el-menu-item) {
  border-radius: var(--mr-radius-sm);
  margin: 4px 8px;
  width: auto;
  transition:
    background-color var(--mr-transition-fast),
    color var(--mr-transition-fast);
}

.nav-drawer :deep(.el-menu-item.is-active) {
  background: var(--el-color-primary-light-9) !important;
  color: var(--el-color-primary) !important;
  font-weight: 600;
}

@media (max-width: 900px) {
  .menu-btn {
    display: inline-flex;
  }
  .side-desktop {
    display: none;
  }
  .logo-text {
    font-size: 14px;
  }
  .main-pane {
    padding: 14px 14px 22px;
  }
  .top-bar {
    padding: 10px 14px 10px 6px;
  }
}
</style>
