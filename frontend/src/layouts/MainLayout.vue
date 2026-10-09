<script setup lang="ts">
import {
  ArrowDown,
  Connection,
  CopyDocument,
  Cpu,
  EditPen,
  Film,
  FolderOpened,
  Menu as IconMenu,
  Setting,
  Star,
  Upload,
} from "@element-plus/icons-vue";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { APP_VERSION } from "../appVersion";
import { fileRouteLocation } from "../composables/useBrowsePath";
import { useAuthStore } from "../stores/auth";
import { useBrowsePrefsStore } from "../stores/browsePrefs";

const auth = useAuthStore();
const prefs = useBrowsePrefsStore();
const router = useRouter();
const route = useRoute();

const drawerVisible = ref(false);

/** 侧栏子菜单 index，须与模板中 el-sub-menu 的 index 一致 */
const FILES_SUBMENU_INDEX = "files-submenu";
const MEDIA_SUBMENU_INDEX = "media-submenu";
const SETTINGS_SUBMENU_INDEX = "settings-submenu";

type TopNavName = "rename" | "folder-merge" | "transfer";
type SettingsLeaf = "settings-storage" | "settings-ai" | "settings-media" | "settings-open-api";
type MediaLeaf = "media-browse" | "media-subscriptions";
type MenuLeafIndex = TopNavName | SettingsLeaf | MediaLeaf;

const isFilesBranch = computed(
  () => route.name === "rename" || route.name === "folder-merge" || route.name === "transfer",
);

const isMediaBranch = computed(
  () =>
    route.name === "media-browse" ||
    route.name === "media-detail" ||
    route.name === "media-subscriptions",
);

const isSettingsBranch = computed(
  () =>
    route.name === "settings-storage" ||
    route.name === "settings-ai" ||
    route.name === "settings-media" ||
    route.name === "settings-open-api",
);

/** 跨越不同主导航分支时重挂菜单，以便 default-openeds 在首次进入时展开对应子菜单 */
const sideMenuInstanceKey = computed(() => {
  if (isSettingsBranch.value) return "nav-settings";
  if (isMediaBranch.value) return "nav-media";
  if (isFilesBranch.value) return "nav-files";
  return "nav-top";
});

const submenuDefaultOpeneds = computed(() => {
  if (isSettingsBranch.value) return [SETTINGS_SUBMENU_INDEX];
  if (isMediaBranch.value) return [MEDIA_SUBMENU_INDEX];
  if (isFilesBranch.value) return [FILES_SUBMENU_INDEX];
  return [];
});

function goTop(name: TopNavName) {
  router.push(fileRouteLocation(name));
}

function goMediaChild(name: MediaLeaf) {
  router.push({ name });
}

function goSettingsChild(name: SettingsLeaf) {
  if (isFilesBranch.value || isMediaBranch.value) {
    prefs.setReturnTo(route.fullPath);
  }
  router.push({ name });
}

function onDrawerSelect(index: string) {
  const leaf = index as MenuLeafIndex;
  if (leaf === "rename" || leaf === "folder-merge" || leaf === "transfer") {
    router.push(fileRouteLocation(leaf));
    drawerVisible.value = false;
    return;
  }
  if (leaf === "media-browse" || leaf === "media-subscriptions") {
    router.push({ name: leaf });
    drawerVisible.value = false;
    return;
  }
  if (
    leaf === "settings-storage" ||
    leaf === "settings-ai" ||
    leaf === "settings-media" ||
    leaf === "settings-open-api"
  ) {
    if (isFilesBranch.value || isMediaBranch.value) prefs.setReturnTo(route.fullPath);
    router.push({ name: leaf });
    drawerVisible.value = false;
  }
}

async function logout() {
  await auth.logout();
  await router.replace({ name: "login" });
}

async function onUserCommand(cmd: string | number) {
  if (cmd === "logout") await logout();
}

const activeMenu = computed(() => {
  if (route.name === "settings-storage") return "settings-storage";
  if (route.name === "settings-ai") return "settings-ai";
  if (route.name === "settings-media") return "settings-media";
  if (route.name === "settings-open-api") return "settings-open-api";
  if (route.name === "media-subscriptions") return "media-subscriptions";
  if (route.name === "media-browse" || route.name === "media-detail") return "media-browse";
  if (route.name === "transfer") return "transfer";
  if (route.name === "folder-merge") return "folder-merge";
  return "rename";
});

const displayVersion = APP_VERSION;
</script>

<template>
  <div class="app-shell">
    <header class="top-bar">
      <div class="top-left">
        <el-button class="menu-btn" text circle @click="drawerVisible = true">
          <el-icon :size="22"><IconMenu /></el-icon>
        </el-button>
        <a href="#" class="logo" @click.prevent="goTop('rename')">
          <span class="logo-mark">MR</span>
          <span class="logo-text">智能文件重命名</span>
        </a>
      </div>
      <div class="top-right">
        <el-dropdown trigger="click" @command="onUserCommand">
          <button type="button" class="user-trigger" :title="auth.user?.username || '账户'">
            <span class="user-trigger-name">{{ auth.user?.username || "账户" }}</span>
            <el-icon class="user-trigger-caret"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled class="user-menu-version">
                版本 {{ displayVersion }}
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="body">
      <aside class="side-desktop" aria-label="主导航">
        <div class="side-label">功能</div>
        <el-menu
          :key="sideMenuInstanceKey"
          :default-active="activeMenu"
          :default-openeds="submenuDefaultOpeneds"
          class="side-menu"
        >
          <el-sub-menu :index="FILES_SUBMENU_INDEX">
            <template #title>
              <el-icon><FolderOpened /></el-icon>
              <span>文件管理</span>
            </template>
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
          </el-sub-menu>
          <el-sub-menu :index="MEDIA_SUBMENU_INDEX">
            <template #title>
              <el-icon><Film /></el-icon>
              <span>影视</span>
            </template>
            <el-menu-item index="media-browse" @click="goMediaChild('media-browse')">
              <el-icon><Film /></el-icon>
              <span>影视发现</span>
            </el-menu-item>
            <el-menu-item index="media-subscriptions" @click="goMediaChild('media-subscriptions')">
              <el-icon><Star /></el-icon>
              <span>想看列表</span>
            </el-menu-item>
          </el-sub-menu>
          <el-sub-menu :index="SETTINGS_SUBMENU_INDEX">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统配置</span>
            </template>
            <el-menu-item index="settings-storage" @click="goSettingsChild('settings-storage')">
              <el-icon><FolderOpened /></el-icon>
              <span>存储挂载</span>
            </el-menu-item>
            <el-menu-item index="settings-ai" @click="goSettingsChild('settings-ai')">
              <el-icon><Cpu /></el-icon>
              <span>AI 服务</span>
            </el-menu-item>
            <el-menu-item index="settings-media" @click="goSettingsChild('settings-media')">
              <el-icon><Film /></el-icon>
              <span>影视数据源</span>
            </el-menu-item>
            <el-menu-item index="settings-open-api" @click="goSettingsChild('settings-open-api')">
              <el-icon><Connection /></el-icon>
              <span>开放接口</span>
            </el-menu-item>
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
        <el-sub-menu :index="FILES_SUBMENU_INDEX">
          <template #title>
            <el-icon><FolderOpened /></el-icon>
            <span>文件管理</span>
          </template>
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
        </el-sub-menu>
        <el-sub-menu :index="MEDIA_SUBMENU_INDEX">
          <template #title>
            <el-icon><Film /></el-icon>
            <span>影视</span>
          </template>
          <el-menu-item index="media-browse">
            <el-icon><Film /></el-icon>
            <span>影视发现</span>
          </el-menu-item>
          <el-menu-item index="media-subscriptions">
            <el-icon><Star /></el-icon>
            <span>想看列表</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu :index="SETTINGS_SUBMENU_INDEX">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统配置</span>
          </template>
          <el-menu-item index="settings-storage">
            <el-icon><FolderOpened /></el-icon>
            <span>存储挂载</span>
          </el-menu-item>
          <el-menu-item index="settings-ai">
            <el-icon><Cpu /></el-icon>
            <span>AI 服务</span>
          </el-menu-item>
          <el-menu-item index="settings-media">
            <el-icon><Film /></el-icon>
            <span>影视数据源</span>
          </el-menu-item>
          <el-menu-item index="settings-open-api">
            <el-icon><Connection /></el-icon>
            <span>开放接口</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-drawer>
  </div>
</template>

<style scoped>
.app-shell {
  height: 100dvh;
  max-height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--mr-bg-page);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 16px 0 8px;
  background: var(--mr-bg-elevated);
  border-bottom: 1px solid var(--mr-border-soft);
  flex-shrink: 0;
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
  min-width: 44px;
  min-height: 44px;
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
  cursor: pointer;
  transition: opacity var(--mr-transition-fast);
}

.logo:hover {
  opacity: 0.9;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--el-color-primary);
  color: var(--color-on-primary);
  font-weight: 700;
  font-size: 12px;
  letter-spacing: -0.5px;
  flex-shrink: 0;
}

.logo-text {
  font-weight: 700;
  font-size: 15px;
  color: var(--mr-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.03em;
}

.top-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 160px;
  margin: 0;
  padding: 5px 10px;
  border: 1px solid var(--mr-border-soft);
  border-radius: 8px;
  background: var(--color-muted);
  color: var(--mr-text);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.user-trigger:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.user-trigger-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-trigger-caret {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--mr-text-secondary);
}

.user-menu-version {
  font-variant-numeric: tabular-nums;
  cursor: default !important;
}

.body {
  flex: 1;
  display: flex;
  min-height: 0;
  width: 100%;
}

.side-desktop {
  width: 216px;
  flex-shrink: 0;
  padding: 14px 10px 16px;
  background: var(--mr-bg-elevated);
  border-right: 1px solid var(--mr-border-soft);
  overflow-y: auto;
}

.side-label {
  padding: 0 10px 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--mr-text-muted);
}

.side-menu {
  border: none;
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: var(--el-color-primary-light-9);
}

.side-menu :deep(.el-menu-item) {
  border-radius: var(--mr-radius-sm);
  margin: 2px 0;
  height: 42px;
  line-height: 42px;
  cursor: pointer;
  transition:
    background-color var(--mr-transition-fast),
    color var(--mr-transition-fast);
}

.side-menu :deep(.el-menu-item:hover) {
  background-color: var(--el-color-primary-light-9) !important;
}

.side-menu :deep(.el-menu-item.is-active) {
  color: var(--el-color-primary) !important;
  background: var(--el-color-primary-light-8) !important;
  font-weight: 600;
}

.side-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
}

.side-menu :deep(.el-sub-menu__title) {
  border-radius: var(--mr-radius-sm);
  margin: 2px 0;
  height: 42px;
  line-height: 42px;
  cursor: pointer;
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

.side-menu :deep(.el-menu) {
  --el-menu-text-color: var(--mr-text-secondary);
  --el-menu-active-color: var(--el-color-primary);
  background: transparent;
}

.main-pane {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 16px 20px 24px;
}

.nav-drawer :deep(.el-sub-menu__title) {
  border-radius: var(--mr-radius-sm);
  margin: 4px 8px;
  width: auto;
  cursor: pointer;
}

.nav-drawer :deep(.el-sub-menu .el-menu-item) {
  margin: 2px 8px 2px 16px;
  min-width: 0;
}

.nav-drawer :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--el-color-primary);
  font-weight: 600;
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
  min-height: 44px;
  cursor: pointer;
}

.nav-drawer :deep(.el-menu-item.is-active) {
  background: var(--el-color-primary-light-8) !important;
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
    padding: 12px 12px 20px;
  }
  .top-bar {
    padding: 0 12px 0 4px;
  }
  .user-trigger {
    max-width: 120px;
  }
}
</style>
