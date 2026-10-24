<script setup lang="ts">
import { ElMessage } from "element-plus";
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { APP_VERSION } from "../appVersion";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const loading = ref(false);
const form = reactive({ username: "", password: "" });
const registerMode = ref(false);

async function submit() {
  loading.value = true;
  try {
    if (registerMode.value) {
      await auth.register(form.username, form.password);
      ElMessage.success("注册成功");
    } else {
      await auth.login(form.username, form.password);
      ElMessage.success("登录成功");
    }
    const redirect = (route.query.redirect as string) || "/";
    await router.replace(redirect);
  } catch (e: unknown) {
    const msg =
      typeof e === "object" && e !== null && "response" in e
        ? String((e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "请求失败")
        : "请求失败";
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-glow" aria-hidden="true" />
    <div class="login-card">
      <div class="brand">
        <span class="brand-mark">MR</span>
        <h1 class="brand-title">电影机器人</h1>
        <p class="brand-sub">Movie Robot Studio</p>
        <p class="brand-tagline">在 NAS 挂载目录中浏览文件，用 AI 生成规范影视文件名</p>
      </div>

      <el-form class="login-form" label-position="top" @submit.prevent="submit">
        <el-form-item :label="registerMode ? '用户名' : '用户名 / 账号'">
          <el-input
            v-model="form.username"
            autocomplete="username"
            size="large"
            :placeholder="registerMode ? '设置管理员用户名' : 'admin 或运维账号'"
          />
        </el-form-item>
        <el-form-item :label="registerMode ? '密码' : '登录密码'">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            size="large"
            show-password
            placeholder="••••••••"
          />
        </el-form-item>
        <el-button
          type="primary"
          native-type="submit"
          :loading="loading"
          size="large"
          class="submit-btn"
        >
          {{ registerMode ? "注册并登录" : "登录" }}
        </el-button>
      </el-form>

      <button type="button" class="toggle-link" @click="registerMode = !registerMode">
        {{ registerMode ? "已有账号？去登录" : "首次部署？尝试注册" }}
      </button>

      <div class="node-pill">
        <span class="node-dot" />
        <span>节点状态: Studio · v{{ APP_VERSION }}</span>
      </div>
    </div>

    <p class="login-foot">Movie Robot Studio · Cinematic Archival Engine · v{{ APP_VERSION }}</p>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 20px 24px;
  box-sizing: border-box;
  background: var(--surface-lowest, #0e0e10);
  overflow: hidden;
}

.login-glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 50% 40% at 50% 42%, rgba(245, 158, 11, 0.12), transparent 70%),
    radial-gradient(ellipse 40% 30% at 80% 90%, rgba(16, 185, 129, 0.04), transparent 60%);
  pointer-events: none;
}

.login-card {
  position: relative;
  width: min(420px, 100%);
  padding: 28px 28px 22px;
  border-radius: 12px;
  background: #18181b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.8);
}

.brand {
  text-align: center;
  margin-bottom: 22px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: 12px;
  border-radius: 8px;
  background: var(--el-color-primary);
  color: var(--color-on-primary);
  font-weight: 700;
  font-size: 14px;
  box-shadow: 0 2px 10px rgba(245, 158, 11, 0.25);
}

.brand-title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--mr-text);
}

.brand-sub {
  margin: 4px 0 0;
  font-family: var(--mr-font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--mr-text-secondary);
}

.brand-tagline {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.55;
  color: var(--mr-text-muted);
}

.login-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: var(--mr-text-secondary);
}

.login-form :deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.35);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08) inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.55) inset;
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.22);
}

.submit-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.toggle-link {
  display: block;
  width: 100%;
  margin: 14px 0 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--mr-text-secondary);
  font: inherit;
  font-size: 12px;
  text-align: center;
  cursor: pointer;
}

.toggle-link:hover {
  color: var(--el-color-primary);
}

.node-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 18px auto 0;
  padding: 6px 12px;
  border-radius: 6px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  font-family: var(--mr-font-mono);
  font-size: 11px;
  color: #10b981;
  width: fit-content;
  max-width: 100%;
}

.node-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.login-foot {
  position: relative;
  margin: 28px 0 0;
  font-family: var(--mr-font-mono);
  font-size: 11px;
  color: #52525b;
  text-align: center;
}

@media (max-width: 480px) {
  .login-page {
    padding: 40px 16px 20px;
    justify-content: flex-start;
  }
  .login-card {
    padding: 22px 18px 18px;
  }
}
</style>
