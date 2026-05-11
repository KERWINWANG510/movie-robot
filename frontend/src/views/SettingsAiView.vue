<script setup lang="ts">
import { Cpu, EditPen, Key, MagicStick } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import http from "../api/http";
import "../styles/settings-views.css";
import { useAuthStore } from "../stores/auth";
import { settingsErrMsg } from "../utils/settingsHttp";

const auth = useAuthStore();

const loading = ref(false);
const saving = ref(false);
const modelsLoading = ref(false);
const prefLoading = ref(false);

const form = reactive({
  ai_provider: "custom",
  openai_base_url: "",
  openai_model: "",
  rename_instruction: "",
});

type ProviderPreset = { id: string; label: string; base_url: string };
const aiPresets = ref<ProviderPreset[]>([]);

const providerSelectOptions = computed(() => [
  ...aiPresets.value.map((p) => ({ value: p.id, label: p.label })),
  { value: "custom", label: "自定义（手动填写 API Base URL）" },
]);

const effectiveBasePreview = computed(() => {
  if (form.ai_provider === "custom") {
    return (form.openai_base_url || "").trim();
  }
  const hit = aiPresets.value.find((p) => p.id === form.ai_provider);
  return hit?.base_url?.trim() ?? "";
});

const apiKeyInput = ref("");
const apiKeySavedInDb = ref(false);

type ModelOpt = { id: string; label: string };
const modelOptions = ref<ModelOpt[]>([]);

async function loadAiPresets() {
  try {
    const { data } = await http.get<{ providers: ProviderPreset[] }>("/settings/ai/providers");
    aiPresets.value = data.providers ?? [];
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  }
}

async function loadSettings() {
  loading.value = true;
  try {
    const { data } = await http.get<{
      ai_provider: string;
      openai_base_url: string;
      openai_model: string;
      rename_instruction: string;
      api_key_saved_in_db: boolean;
    }>("/settings");
    form.ai_provider = data.ai_provider || "custom";
    form.openai_base_url = data.openai_base_url;
    form.openai_model = data.openai_model;
    form.rename_instruction = data.rename_instruction ?? "";
    apiKeySavedInDb.value = data.api_key_saved_in_db;
    apiKeyInput.value = "";
    if (form.openai_model && !modelOptions.value.some((m) => m.id === form.openai_model)) {
      modelOptions.value = [{ id: form.openai_model, label: form.openai_model }, ...modelOptions.value];
    }
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    loading.value = false;
  }
}

async function saveAi() {
  saving.value = true;
  try {
    const body: Record<string, unknown> = {
      ai_provider: form.ai_provider,
      openai_model: form.openai_model,
      rename_instruction: form.rename_instruction,
    };
    if (form.ai_provider === "custom") {
      body.openai_base_url = form.openai_base_url;
    } else {
      body.openai_base_url = "";
    }
    if (apiKeyInput.value.trim()) {
      body.openai_api_key = apiKeyInput.value.trim();
    }
    await http.patch("/settings", body);
    ElMessage.success("AI 配置已保存");
    apiKeyInput.value = "";
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
    await http.patch("/settings", { openai_api_key: "" });
    ElMessage.success("已清除库内保存的密钥");
    apiKeyInput.value = "";
    await loadSettings();
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    saving.value = false;
  }
}

async function fetchModels() {
  modelsLoading.value = true;
  try {
    const probeBody: Record<string, string | undefined> = {
      ai_provider: form.ai_provider,
      openai_api_key: apiKeyInput.value.trim() || undefined,
    };
    if (form.ai_provider === "custom") {
      probeBody.openai_base_url = form.openai_base_url.trim() || undefined;
    }
    const { data } = await http.post<{ models: ModelOpt[] }>("/settings/models/list", probeBody);
    modelOptions.value = data.models;
    if (data.models.length === 0) {
      ElMessage.warning("未解析到模型列表，请检查网关是否提供 /v1/models");
    } else {
      ElMessage.success(`已加载 ${data.models.length} 个模型`);
      if (form.openai_model && !data.models.some((m) => m.id === form.openai_model)) {
        /* 保留当前输入 */
      } else if (!form.openai_model && data.models[0]) {
        form.openai_model = data.models[0].id;
      }
    }
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    modelsLoading.value = false;
  }
}

async function onPrefChange(v: string | number | boolean) {
  const next = Boolean(v);
  prefLoading.value = true;
  try {
    await auth.updatePreference(next);
    ElMessage.success("命名模式已更新");
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    prefLoading.value = false;
  }
}

onMounted(() => {
  loadAiPresets();
  loadSettings();
});
</script>

<template>
  <div class="settings-page-wrap has-sticky-actionbar" v-loading="loading">
    <div class="page-head mr-page-intro">
      <h1 class="mr-page-title">AI 服务</h1>
      <p class="mr-page-desc">配置大模型网关、模型与重命名说明；命名模式控制是否在重命名前必须预览确认。</p>
    </div>

    <el-card class="block-card" shadow="never">
      <template #header>
        <div class="card-head mr-card-head">
          <el-icon class="head-ic"><Cpu /></el-icon>
          <span>AI 服务</span>
        </div>
      </template>
      <el-form label-position="top" class="nice-form">
        <el-form-item label="AI 服务商">
          <el-select v-model="form.ai_provider" placeholder="选择服务商" filterable class="provider-select">
            <el-option
              v-for="opt in providerSelectOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <div class="hint">
            选择内置服务商时只需填写 API Key，Base URL 由系统默认提供；选择「自定义」时需自行填写 Base URL 与 Key。
          </div>
        </el-form-item>
        <el-form-item v-if="form.ai_provider !== 'custom'" label="API Base URL（内置）">
          <el-input :model-value="effectiveBasePreview" readonly disabled />
          <div class="hint">以上为当前服务商默认地址，无需手动填写。</div>
        </el-form-item>
        <el-form-item v-else label="API Base URL">
          <el-input
            v-model="form.openai_base_url"
            placeholder="OpenAI 兼容网关根路径，如 https://api.openai.com/v1"
            clearable
          />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="apiKeyInput"
            type="password"
            show-password
            :placeholder="
              apiKeySavedInDb ? '已保存密钥；输入新值可覆盖，留空保存则不修改' : '请输入密钥；保存后写入数据库'
            "
            clearable
          />
          <div v-if="apiKeySavedInDb" class="hint-row">
            <el-tag size="small" type="success" effect="plain">库内已保存密钥</el-tag>
            <el-button text type="danger" size="small" :disabled="saving" @click="clearSavedKey">
              清除库内密钥
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="模型">
          <div class="model-row">
            <el-select
              v-model="form.openai_model"
              filterable
              allow-create
              default-first-option
              placeholder="先获取列表或手动输入模型 ID"
              class="model-select"
            >
              <el-option v-for="m in modelOptions" :key="m.id" :label="m.label" :value="m.id" />
            </el-select>
            <el-button type="primary" :loading="modelsLoading" @click="fetchModels">
              <el-icon class="btn-ic"><Key /></el-icon>
              获取模型列表
            </el-button>
          </div>
          <div class="hint">
            填写密钥（及自定义模式下的 Base URL）后可拉取远端模型；部分网关不支持 /v1/models，可直接输入模型 ID。
          </div>
        </el-form-item>
        <el-form-item>
          <template #label>
            <span class="label-with-icon">
              <el-icon><EditPen /></el-icon>
              重命名说明（自然语言）
            </span>
          </template>
          <el-input
            v-model="form.rename_instruction"
            type="textarea"
            :rows="5"
            maxlength="4000"
            show-word-limit
            placeholder="例如：统一改成「日期_原标题」格式；英文电影用英文片名；去掉文件名里的站点广告字样；保留原有扩展名……"
            class="instruction-input"
          />
          <div class="hint">预览时将发送给 AI 并优先遵守；留空则按默认规则生成建议文件名。</div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="block-card mt" shadow="never">
      <template #header>
        <div class="card-head mr-card-head">
          <el-icon class="head-ic"><MagicStick /></el-icon>
          <span>命名模式</span>
        </div>
      </template>
      <div class="pref-body">
        <div class="pref-label">重命名前是否必须预览确认</div>
        <p class="pref-tip">关闭后可使用「全自动」流程；开启后服务端将校验预览会话，更安全。</p>
        <el-switch
          :model-value="auth.user?.auto_rename_without_preview ?? false"
          :loading="prefLoading"
          active-text="全自动"
          inactive-text="预览确认"
          inline-prompt
          size="large"
          @change="onPrefChange"
        />
      </div>
    </el-card>

    <div class="mr-sticky-actionbar">
      <div class="mr-sticky-actionbar__inner">
        <el-button type="primary" size="large" :loading="saving" class="save-btn" @click="saveAi">保存 AI 配置</el-button>
      </div>
    </div>
  </div>
</template>
