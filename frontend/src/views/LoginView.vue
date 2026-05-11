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
    <el-card class="card" shadow="always">
      <template #header>
        <div class="hdr">
          <span class="hdr-title">{{ registerMode ? "注册账号" : "登录" }}</span>
          <span class="hdr-sub">智能文件重命名</span>
        </div>
      </template>
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" autocomplete="current-password" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
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
</template>

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
  overflow-x: hidden;
}

.page-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(700px 420px at 18% 12%, rgba(58, 124, 232, 0.14), transparent 60%),
    radial-gradient(560px 380px at 88% 78%, rgba(92, 184, 122, 0.1), transparent 55%),
    linear-gradient(165deg, var(--mr-bg-page), #e4eaf3 100%);
  pointer-events: none;
}

.card {
  position: relative;
  width: min(420px, 100%);
  border-radius: var(--mr-radius-lg);
  border: 1px solid var(--mr-border-soft);
  box-shadow: var(--mr-shadow-md);
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

.toggle {
  text-align: center;
  padding-top: 4px;
}

.toggle :deep(.el-link) {
  font-size: 13px;
}
</style>
