<script setup lang="ts">
import { ElMessage } from "element-plus";
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

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
  <div class="page">
    <div class="page-bg" aria-hidden="true" />
    <div class="login-stage">
      <div class="brand-block">
        <div class="brand-mark" aria-hidden="true">MR</div>
        <h1 class="brand-name">智能文件重命名</h1>
        <p class="brand-tagline">在 NAS 挂载目录中浏览文件，用 AI 生成规范文件名</p>
      </div>

      <el-card class="card" shadow="never">
        <template #header>
          <div class="hdr">
            <span class="hdr-title">{{ registerMode ? "注册账号" : "登录" }}</span>
            <span class="hdr-sub">{{ registerMode ? "创建首个管理员账号" : "使用账号继续" }}</span>
          </div>
        </template>
        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item label="用户名">
            <el-input v-model="form.username" autocomplete="username" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              autocomplete="current-password"
              size="large"
              show-password
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" native-type="submit" :loading="loading" size="large" class="submit-btn">
              {{ registerMode ? "注册并登录" : "登录" }}
            </el-button>
          </el-form-item>
          <div class="toggle">
            <el-link type="primary" @click="registerMode = !registerMode">
              {{ registerMode ? "已有账号？去登录" : "首次部署？尝试注册（若管理员未关闭）" }}
            </el-link>
          </div>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 20px;
  box-sizing: border-box;
  overflow-x: hidden;
}

.page-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(720px 420px at 15% 10%, rgba(13, 148, 136, 0.16), transparent 60%),
    radial-gradient(560px 380px at 90% 85%, rgba(234, 88, 12, 0.08), transparent 55%),
    var(--mr-bg-page);
  pointer-events: none;
}

.login-stage {
  position: relative;
  width: min(420px, 100%);
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.brand-block {
  text-align: center;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 14px;
  border-radius: 14px;
  background: var(--el-color-primary);
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  letter-spacing: -0.5px;
}

.brand-name {
  margin: 0 0 8px;
  font-size: clamp(1.75rem, 5vw, 2.125rem);
  font-weight: 700;
  letter-spacing: -0.04em;
  color: var(--mr-text);
  line-height: 1.2;
}

.brand-tagline {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--mr-text-secondary);
  line-height: 1.55;
}

.card {
  width: 100%;
  border-radius: var(--mr-radius-lg);
  border: 1px solid var(--mr-border-soft);
  background: var(--color-card);
}

.hdr {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hdr-title {
  font-weight: 700;
  font-size: 1.125rem;
  letter-spacing: -0.02em;
  color: var(--mr-text);
}

.hdr-sub {
  font-size: 12px;
  font-weight: 500;
  color: var(--mr-text-muted);
}

.submit-btn {
  width: 100%;
}

.toggle {
  text-align: center;
  padding-top: 4px;
}

.toggle :deep(.el-link) {
  font-size: 13px;
  cursor: pointer;
}

@media (max-width: 480px) {
  .page {
    padding: 20px 16px;
    align-items: flex-start;
    padding-top: 48px;
  }

  .login-stage {
    gap: 22px;
  }
}
</style>
