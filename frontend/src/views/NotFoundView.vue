<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const secondsLeft = ref(5);
let timer: ReturnType<typeof setInterval> | null = null;

function goHome() {
  router.replace({ name: "rename" });
}

onMounted(() => {
  timer = setInterval(() => {
    secondsLeft.value -= 1;
    if (secondsLeft.value <= 0) {
      if (timer) clearInterval(timer);
      timer = null;
      goHome();
    }
  }, 1000);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="not-found-page">
    <div class="not-found-card">
      <div class="code">404</div>
      <h1 class="title">页面不存在</h1>
      <p class="desc">您访问的地址可能已变更或输入有误。</p>
      <p class="countdown">
        <span class="num">{{ Math.max(0, secondsLeft) }}</span>
        秒后自动返回首页
      </p>
      <el-button type="primary" size="large" @click="goHome">立即返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.not-found-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background:
    radial-gradient(900px 420px at 50% -10%, rgba(58, 124, 232, 0.12), transparent 55%),
    linear-gradient(165deg, var(--mr-bg-page) 0%, #e8edf4 100%);
}

.not-found-card {
  width: 100%;
  max-width: 420px;
  text-align: center;
  padding: 36px 28px 32px;
  border-radius: var(--mr-radius-lg);
  background: var(--mr-bg-elevated);
  border: 1px solid var(--mr-border-soft);
  box-shadow: var(--mr-shadow-md);
}

.code {
  font-size: 56px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  background: linear-gradient(135deg, var(--el-color-primary), #5cb87a);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 12px;
}

.title {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 700;
  color: var(--mr-text);
}

.desc {
  margin: 0 0 20px;
  font-size: 14px;
  color: var(--mr-text-secondary);
  line-height: 1.65;
}

.countdown {
  margin: 0 0 22px;
  font-size: 14px;
  color: var(--mr-text-secondary);
}

.countdown .num {
  display: inline-block;
  min-width: 1.2em;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--el-color-primary);
}
</style>
