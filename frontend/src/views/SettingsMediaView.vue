<script setup lang="ts">
import { Film, Key } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";
import "../styles/settings-views.css";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { settingsErrMsg } from "../utils/settingsHttp";

const router = useRouter();
const prefs = useBrowsePrefsStore();
const returnTo = computed(() => prefs.returnTo);

function goBackToFiles() {
  const target = prefs.returnTo || "/files";
  prefs.setReturnTo(null);
  void router.push(target);
}

const loading = ref(false);
const saving = ref(false);
const tmdbKeyInput = ref("");
const tmdbKeySavedInDb = ref(false);

async function loadSettings() {
  loading.value = true;
  try {
    const { data } = await http.get<{ tmdb_api_key_saved_in_db: boolean }>("/settings");
    tmdbKeySavedInDb.value = Boolean(data.tmdb_api_key_saved_in_db);
    tmdbKeyInput.value = "";
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    loading.value = false;
  }
}

async function saveMedia() {
  const next = tmdbKeyInput.value.trim();
  if (!next) {
    if (tmdbKeySavedInDb.value) {
      ElMessage.info("密钥未更改");
      return;
    }
    ElMessage.warning("请输入 TMDB API Key");
    return;
  }
  saving.value = true;
  try {
    await http.patch("/settings", { tmdb_api_key: next });
    ElMessage.success("影视数据源配置已保存");
    tmdbKeyInput.value = "";
    await loadSettings();
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    saving.value = false;
  }
}

async function clearSavedKey() {
  saving.value = true;
  try {
    await http.patch("/settings", { tmdb_api_key: "" });
    ElMessage.success("已清除库内保存的 TMDB API Key");
    tmdbKeyInput.value = "";
    await loadSettings();
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadSettings();
});
</script>

<template>
  <div class="settings-page-wrap has-sticky-actionbar" v-loading="loading">
    <div class="page-head mr-page-intro">
      <h1 class="mr-page-title">影视数据源</h1>
      <p class="mr-page-desc">
        配置 TMDB API Key 后，可浏览正在热映的电影、正在热播的电视剧，并将条目加入「想看」列表。
      </p>
    </div>

    <el-card class="block-card" shadow="never">
      <template #header>
        <div class="card-head mr-card-head">
          <el-icon class="head-ic"><Film /></el-icon>
          <span>TMDB</span>
        </div>
      </template>
      <el-form label-position="top" class="nice-form">
        <el-form-item label="TMDB API Key">
          <el-input
            v-model="tmdbKeyInput"
            type="password"
            show-password
            :placeholder="
              tmdbKeySavedInDb
                ? '已保存密钥；输入新值可覆盖，留空保存则不修改'
                : '请输入 API Key；保存后写入数据库'
            "
            clearable
          >
            <template #prefix>
              <el-icon><Key /></el-icon>
            </template>
          </el-input>
          <div v-if="tmdbKeySavedInDb" class="hint-row">
            <el-tag size="small" type="success" effect="plain">库内已保存密钥</el-tag>
            <el-button text type="danger" size="small" :disabled="saving" @click="clearSavedKey">
              清除库内密钥
            </el-button>
          </div>
          <div class="hint">
            请前往
            <a href="https://www.themoviedb.org/settings/api" target="_blank" rel="noopener noreferrer"
              >TMDB 账号设置</a
            >
            免费申请 API Key（v3）。本应用请求语言固定为简体中文（zh-CN）。密钥仅保存在本机，不会回显明文。
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="mr-sticky-actionbar">
      <div class="mr-sticky-actionbar__inner">
        <el-button v-if="returnTo" size="large" @click="goBackToFiles">返回文件页</el-button>
        <el-button type="primary" size="large" :loading="saving" class="save-btn" @click="saveMedia">
          保存配置
        </el-button>
      </div>
    </div>
  </div>
</template>
