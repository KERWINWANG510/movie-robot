<script setup lang="ts">
import {
  ArrowDown,
  Connection,
  Cpu,
  Film,
  FolderOpened,
  Menu as IconMenu,
  Setting,
  Star,
} from "@element-plus/icons-vue";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import http from "../api/http";
import { APP_VERSION } from "../appVersion";
import { fileRouteLocation } from "../composables/useBrowsePath";
import { useAuthStore } from "../stores/auth";
import { useBrowsePrefsStore } from "../stores/browsePrefs";

const auth = useAuthStore();
const prefs = useBrowsePrefsStore();
const router = useRouter();
const route = useRoute();

const drawerVisible = ref(false);
const mountReady = ref(false);
const mountPath = ref("");

/** 侧栏子菜单 index，须与模板中 el-sub-menu 的 index 一致 */
const MEDIA_SUBMENU_INDEX = "media-submenu";
const SETTINGS_SUBMENU_INDEX = "settings-submenu";

type FileModeName = "rename" | "folder-merge" | "transfer";
type SettingsLeaf = "settings-storage" | "settings-ai" | "settings-media" | "settings-open-api";
type MediaLeaf = "media-browse" | "media-subscriptions";
type MenuLeafIndex = "files" | SettingsLeaf | MediaLeaf;

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

const sideMenuInstanceKey = computed(() => {
  if (isSettingsBranch.value) return "nav-settings";
  if (isMediaBranch.value) return "nav-media";
  if (isFilesBranch.value) return "nav-files";
  return "nav-top";
});

const submenuDefaultOpeneds = computed(() => {
  if (isSettingsBranch.value) return [SETTINGS_SUBMENU_INDEX];
  if (isMediaBranch.value) return [MEDIA_SUBMENU_INDEX];
  return [];
});

const topCrumb = computed(() => {
  if (isFilesBranch.value) return "本地媒体挂载卷";
  if (isMediaBranch.value) return "影视媒体库";
  if (isSettingsBranch.value) return "系统配置";
  return "工作区";
});

function currentFileMode(): FileModeName {
  if (route.name === "folder-merge") return "folder-merge";
  if (route.name === "transfer") return "transfer";
  return "rename";
}

function goFiles() {
  router.push(fileRouteLocation(isFilesBranch.value ? currentFileMode() : "rename"));
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
  if (leaf === "files") {
    goFiles();
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

async function loadMountMeta() {
  try {
    const { data } = await http.get<{ mount_ready: boolean; mount_path: string }>("/settings");
    mountReady.value = data.mount_ready;
    mountPath.value = (data.mount_path || "").trim();
  } catch {
    mountReady.value = false;
    mountPath.value = "";
  }
}

const activeMenu = computed(() => {
  if (route.name === "settings-storage") return "settings-storage";
  if (route.name === "settings-ai") return "settings-ai";
  if (route.name === "settings-media") return "settings-media";
  if (route.name === "settings-open-api") return "settings-open-api";
  if (route.name === "media-subscriptions") return "media-subscriptions";
  if (route.name === "media-browse" || route.name === "media-detail") return "media-browse";
  if (isFilesBranch.value) return "files";
  return "files";
});

const displayVersion = APP_VERSION;
const userInitial = computed(() => {
  const name = (auth.user?.username || "A").trim();
  return (name[0] || "A").toUpperCase();
});

onMounted(() => {
  void loadMountMeta();
});
</script>

<template>
  <div class="app-shell">
    <aside class="side-desktop" aria-label="主导航">
      <div class="side-top">
        <a href="#" class="brand" @click.prevent="goFiles">
          <span class="brand-mark">MR</span>
          <span class="brand-text">
            <span class="brand-title">电影机器人</span>
            <span class="brand-sub">Movie Robot Studio</span>
          </span>
        </a>

        <div class="side-label">功能</div>
        <el-menu
          :key="sideMenuInstanceKey"
          :default-active="activeMenu"
          :default-openeds="submenuDefaultOpeneds"
          class="side-menu"
        >
          <el-menu-item index="files" @click="goFiles">
            <el-icon><FolderOpened /></el-icon>
            <span>文件管理</span>
          </el-menu-item>
          <el-sub-menu :index="MEDIA_SUBMENU_INDEX">
            <template #title>
              <el-icon><Film /></el-icon>
              <span>影视媒体库</span>
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
      </div>

      <div class="side-bottom">
        <div class="mount-pill">
          <div class="mount-pill-row">
            <span class="mount-pill-label">{{ mountReady ? "挂载点就绪" : "挂载未配置" }}</span>
            <span class="mount-pill-pct" :class="{ ok: mountReady }">{{ mountReady ? "OK" : "—" }}</span>
          </div>
          <div class="mount-pill-bar">
            <div class="mount-pill-fill" :style="{ width: mountReady ? '100%' : '8%' }" />
          </div>
          <div v-if="mountPath" class="mount-pill-path" :title="mountPath">{{ mountPath }}</div>
        </div>
        <div class="side-health" :class="{ ok: mountReady }">
          <span class="health-dot" />
          <span>系统健康状态: {{ mountReady ? "正常" : "待配置" }}</span>
        </div>
      </div>
    </aside>

    <div class="content-col">
      <header class="top-bar">
        <div class="top-left">
          <el-button class="menu-btn" text circle @click="drawerVisible = true">
            <el-icon :size="22"><IconMenu /></el-icon>
          </el-button>
          <div class="top-crumb">
            <span class="crumb-muted">工作区</span>
            <span class="crumb-sep">/</span>
            <span class="crumb-active">{{ topCrumb }}</span>
          </div>
          <span class="env-badge">v{{ displayVersion }}</span>
        </div>
        <div class="top-right">
          <el-dropdown trigger="click" @command="onUserCommand">
            <button type="button" class="user-trigger" :title="auth.user?.username || '账户'">
              <span class="user-avatar">{{ userInitial }}</span>
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
        <el-menu-item index="files">
          <el-icon><FolderOpened /></el-icon>
          <span>文件管理</span>
        </el-menu-item>
        <el-sub-menu :index="MEDIA_SUBMENU_INDEX">
          <template #title>
            <el-icon><Film /></el-icon>
            <span>影视媒体库</span>
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
  overflow: hidden;
  background: var(--surface-lowest, #0e0e10);
}

.side-desktop {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px 12px;
  background: var(--surface-low, #1b1b1d);
  border-right: 1px solid var(--mr-border-soft);
  overflow: hidden;
}

.side-top {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px 12px;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--el-color-primary);
  color: var(--color-on-primary);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: -0.5px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.2;
}

.brand-title {
  font-weight: 700;
  font-size: 15px;
  color: var(--mr-text);
  letter-spacing: -0.03em;
}

.brand-sub {
  font-family: var(--mr-font-mono);
  font-size: 11px;
  color: var(--mr-text-secondary);
  margin-top: 2px;
}

.side-label {
  padding: 4px 12px 6px;
  font-family: var(--mr-font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--mr-text-muted);
}

.side-menu {
  border: none;
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.04);
  --el-menu-text-color: var(--mr-text-secondary);
  --el-menu-active-color: var(--el-color-primary);
}

.side-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin: 2px 0;
  height: 40px;
  line-height: 40px;
  border-left: 2px solid transparent;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.side-menu :deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.04) !important;
  color: #e4e4e7 !important;
}

.side-menu :deep(.el-menu-item.is-active) {
  color: var(--el-color-primary) !important;
  background: var(--surface-high, #2b2b2e) !important;
  font-weight: 600;
  border-left-color: var(--el-color-primary);
}

.side-menu :deep(.el-sub-menu__title) {
  border-radius: 8px;
  margin: 2px 0;
  height: 40px;
  line-height: 40px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.side-menu :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.04) !important;
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
  background: transparent;
}

.side-bottom {
  flex-shrink: 0;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mount-pill {
  padding: 10px;
  border-radius: 8px;
  background: var(--surface-container, #222225);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mount-pill-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.mount-pill-label,
.mount-pill-pct {
  font-family: var(--mr-font-mono);
  font-size: 11px;
  color: var(--mr-text-secondary);
}

.mount-pill-pct.ok {
  color: var(--el-color-primary);
  font-weight: 600;
}

.mount-pill-bar {
  height: 6px;
  border-radius: 9999px;
  background: var(--surface-highest, #343438);
  overflow: hidden;
}

.mount-pill-fill {
  height: 100%;
  border-radius: 9999px;
  background: var(--el-color-primary);
  transition: width 0.2s ease;
}

.mount-pill-path {
  font-family: var(--mr-font-mono);
  font-size: 10px;
  color: var(--mr-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-health {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 4px;
  font-family: var(--mr-font-mono);
  font-size: 11px;
  color: var(--mr-text-secondary);
}

.side-health.ok {
  color: var(--el-color-success);
}

.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--mr-text-muted);
  flex-shrink: 0;
}

.side-health.ok .health-dot {
  background: var(--el-color-success);
}

.content-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 24px;
  background: color-mix(in srgb, var(--surface, #131315) 80%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--mr-border-soft);
  flex-shrink: 0;
  z-index: 20;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.menu-btn {
  display: none;
  color: var(--mr-text-secondary);
  min-width: 44px;
  min-height: 44px;
}

.top-crumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  min-width: 0;
}

.crumb-muted {
  color: var(--mr-text-secondary);
}

.crumb-sep {
  color: var(--mr-text-muted);
}

.crumb-active {
  color: var(--el-color-primary);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.env-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: var(--mr-font-mono);
  font-size: 11px;
  color: var(--mr-text-secondary);
  background: var(--surface-high, #2b2b2e);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.top-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 200px;
  margin: 0;
  padding: 4px 8px 4px 4px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--mr-text);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s ease;
}

.user-trigger:hover {
  color: var(--el-color-primary);
}

.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--surface-high, #2b2b2e);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.user-trigger-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-trigger-caret {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--mr-text-muted);
}

.user-menu-version {
  font-variant-numeric: tabular-nums;
  cursor: default !important;
}

.main-pane {
  flex: 1;
  min-width: 0;
  overflow: auto;
  padding: 24px;
  background: var(--surface, #131315);
}

.nav-drawer :deep(.el-sub-menu__title) {
  border-radius: 8px;
  margin: 4px 8px;
  width: auto;
}

.nav-drawer :deep(.el-sub-menu .el-menu-item) {
  margin: 2px 8px 2px 16px;
  min-width: 0;
}

.nav-drawer :deep(.el-menu) {
  border-right: none;
  padding: 4px 0;
  background: transparent;
}

.nav-drawer :deep(.el-menu-item) {
  border-radius: 8px;
  margin: 4px 8px;
  width: auto;
  min-height: 44px;
}

.nav-drawer :deep(.el-menu-item.is-active) {
  background: var(--surface-high, #2b2b2e) !important;
  color: var(--el-color-primary) !important;
  font-weight: 600;
}

@media (max-width: 900px) {
  .side-desktop {
    display: none;
  }
  .menu-btn {
    display: inline-flex;
  }
  .top-bar {
    padding: 0 12px;
  }
  .main-pane {
    padding: 12px 12px 20px;
  }
  .env-badge {
    display: none;
  }
  .user-trigger-name {
    max-width: 72px;
  }
}
</style>
