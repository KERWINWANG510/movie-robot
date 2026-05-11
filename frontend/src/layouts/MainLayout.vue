<script setup lang="ts">
import { CopyDocument, EditPen, Menu as IconMenu, Setting, Upload } from "@element-plus/icons-vue";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const drawerVisible = ref(false);

type NavName = "rename" | "folder-merge" | "transfer" | "settings";

const navItems = computed(() => [
  { name: "rename" as const, title: "文件重命名", icon: EditPen },
  { name: "folder-merge" as const, title: "文件夹合并", icon: CopyDocument },
  { name: "transfer" as const, title: "文件传输", icon: Upload },
  { name: "settings" as const, title: "系统配置", icon: Setting },
]);

function go(name: NavName) {
  router.push({ name });
  drawerVisible.value = false;
}

async function logout() {
  await auth.logout();
  await router.replace({ name: "login" });
}

const activeMenu = computed(() => {
  if (route.name === "settings") return "settings";
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
        <el-menu :key="activeMenu" :default-active="activeMenu" class="side-menu">
          <el-menu-item index="rename" @click="go('rename')">
            <el-icon><EditPen /></el-icon>
            <span>文件重命名</span>
          </el-menu-item>
          <el-menu-item index="folder-merge" @click="go('folder-merge')">
            <el-icon><CopyDocument /></el-icon>
            <span>文件夹合并</span>
          </el-menu-item>
          <el-menu-item index="transfer" @click="go('transfer')">
            <el-icon><Upload /></el-icon>
            <span>文件传输</span>
          </el-menu-item>
          <el-menu-item index="settings" @click="go('settings')">
            <el-icon><Setting /></el-icon>
            <span>系统配置</span>
          </el-menu-item>
        </el-menu>
      </aside>

      <main class="main-pane">
        <router-view />
      </main>
    </div>

    <el-drawer v-model="drawerVisible" direction="ltr" size="260px" title="导航" class="nav-drawer">
      <el-menu :key="activeMenu" :default-active="activeMenu" @select="(i: string) => go(i as NavName)">
        <el-menu-item v-for="item in navItems" :key="item.name" :index="item.name">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, #f0f4f8 0%, #e8eef5 45%, #f5f7fa 100%);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px 10px 8px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 1px 12px rgba(0, 0, 0, 0.06);
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
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: -0.5px;
  flex-shrink: 0;
}

.logo-text {
  font-weight: 600;
  font-size: 16px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.who {
  font-size: 13px;
  color: #909399;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  width: 220px;
  flex-shrink: 0;
  padding: 16px 0 16px 12px;
}

.side-menu {
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.main-pane {
  flex: 1;
  min-width: 0;
  padding: 16px 16px 24px;
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
}
</style>
