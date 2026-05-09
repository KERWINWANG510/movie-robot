<script setup lang="ts">
import { Cpu, EditPen, FolderOpened, Key, MagicStick } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import http from "../api/http";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

function errMsg(e: unknown): string {
  if (typeof e === "object" && e !== null && "response" in e) {
    const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => JSON.stringify(x)).join("; ");
  }
  return "请求失败";
}

const loading = ref(false);
const saving = ref(false);
const modelsLoading = ref(false);
const prefLoading = ref(false);

const form = reactive({
  mount_path: "",
  openai_base_url: "",
  openai_model: "",
  rename_instruction: "",
});
const apiKeyInput = ref("");
const hasSavedKey = ref(false);

type ModelOpt = { id: string; label: string };
const modelOptions = ref<ModelOpt[]>([]);

async function loadSettings() {
  loading.value = true;
  try {
    const { data } = await http.get<{
      mount_path: string;
      openai_base_url: string;
      openai_model: string;
      rename_instruction: string;
      has_openai_api_key: boolean;
    }>("/settings");
    form.mount_path = data.mount_path;
    form.openai_base_url = data.openai_base_url;
    form.openai_model = data.openai_model;
    form.rename_instruction = data.rename_instruction ?? "";
    hasSavedKey.value = data.has_openai_api_key;
    apiKeyInput.value = "";
    if (form.openai_model && !modelOptions.value.some((m) => m.id === form.openai_model)) {
      modelOptions.value = [{ id: form.openai_model, label: form.openai_model }, ...modelOptions.value];
    }
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    loading.value = false;
  }
}

async function saveAll() {
  saving.value = true;
  try {
    const body: Record<string, string> = {
      mount_path: form.mount_path,
      openai_base_url: form.openai_base_url,
      openai_model: form.openai_model,
      rename_instruction: form.rename_instruction,
    };
    if (apiKeyInput.value.trim()) {
      body.openai_api_key = apiKeyInput.value.trim();
    }
    await http.patch("/settings", body);
    ElMessage.success("配置已保存");
    apiKeyInput.value = "";
    await loadSettings();
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    saving.value = false;
  }
}

async function clearSavedKey() {
  saving.value = true;
  try {
    await http.patch("/settings", { openai_api_key: "" });
    ElMessage.success("已清除库内保存的密钥（将使用环境变量中的配置）");
    apiKeyInput.value = "";
    await loadSettings();
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    saving.value = false;
  }
}

async function fetchModels() {
  modelsLoading.value = true;
  try {
    const { data } = await http.post<{ models: ModelOpt[] }>("/settings/models/list", {
      openai_base_url: form.openai_base_url || undefined,
      openai_api_key: apiKeyInput.value.trim() || undefined,
    });
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
    ElMessage.error(errMsg(e));
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
    ElMessage.error(errMsg(e));
  } finally {
    prefLoading.value = false;
  }
}

onMounted(() => {
  loadSettings();
});
</script>

<template>
  <div class="settings-wrap" v-loading="loading">
    <div class="page-head">
      <h1 class="page-title">系统配置</h1>
      <p class="page-desc">
        挂载目录、AI 服务、自然语言重命名说明与命名模式将即时作用于后续浏览与预览任务。
      </p>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="15">
        <el-card class="block-card" shadow="hover">
          <template #header>
            <div class="card-head">
              <el-icon class="head-ic"><FolderOpened /></el-icon>
              <span>存储挂载</span>
            </div>
          </template>
          <el-form label-position="top" class="nice-form">
            <el-form-item label="挂载根目录">
              <el-input
                v-model="form.mount_path"
                placeholder="例如容器内 /data 或 Windows 路径；留空则使用服务端环境变量 MOUNT_PATH"
                clearable
              />
              <div class="hint">须与实际映射到 NAS 的路径一致，保存后立即生效。</div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="block-card mt" shadow="hover">
          <template #header>
            <div class="card-head">
              <el-icon class="head-ic"><Cpu /></el-icon>
              <span>AI 服务</span>
            </div>
          </template>
          <el-form label-position="top" class="nice-form">
            <el-form-item label="API Base URL">
              <el-input v-model="form.openai_base_url" placeholder="OpenAI 兼容网关，如 https://api.openai.com/v1" clearable />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input
                v-model="apiKeyInput"
                type="password"
                show-password
                :placeholder="
                  hasSavedKey ? '已保存密钥；输入新值可覆盖，留空保存则不修改' : '请输入密钥；保存后写入数据库'
                "
                clearable
              />
              <div class="hint-row">
                <el-tag v-if="hasSavedKey" size="small" type="success" effect="plain">库内已保存密钥</el-tag>
                <el-tag v-else size="small" type="info" effect="plain">未在库中保存（使用环境变量）</el-tag>
                <el-button text type="danger" size="small" :disabled="saving" @click="clearSavedKey"> 清除库内密钥 </el-button>
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
              <div class="hint">填写 API 与密钥后可拉取远端模型；部分自建网关可能不支持列表接口，可直接输入模型名。</div>
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
              <div class="hint">
                预览时将发送给 AI 并优先遵守；留空则按默认规则生成建议文件名。
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="9">
        <el-card class="block-card pref-card" shadow="hover">
          <template #header>
            <div class="card-head">
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
      </el-col>
    </el-row>

    <div class="footer-actions">
      <el-button type="primary" size="large" :loading="saving" @click="saveAll">保存全部配置</el-button>
    </div>
  </div>
</template>

<style scoped>
.settings-wrap {
  max-width: 960px;
  margin: 0 auto;
}

.page-head {
  margin-bottom: 20px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  letter-spacing: 0.02em;
}

.page-desc {
  margin: 0;
  font-size: 14px;
  color: #909399;
  line-height: 1.6;
}

.block-card {
  border-radius: 14px;
  border: 1px solid var(--el-border-color-lighter);
}

.block-card :deep(.el-card__header) {
  padding: 14px 18px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
}

.head-ic {
  font-size: 18px;
  color: var(--el-color-primary);
}

.nice-form :deep(.el-form-item__label) {
  font-weight: 500;
}

.hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.hint-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.model-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  width: 100%;
}

.model-select {
  flex: 1;
  min-width: 200px;
}

.btn-ic {
  margin-right: 4px;
  vertical-align: middle;
}

.label-with-icon {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.instruction-input :deep(.el-textarea__inner) {
  border-radius: 10px;
  line-height: 1.55;
}

.mt {
  margin-top: 20px;
}

.pref-card {
  position: sticky;
  top: 72px;
}

.pref-body {
  padding: 4px 0 8px;
}

.pref-label {
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}

.pref-tip {
  font-size: 13px;
  color: #909399;
  line-height: 1.55;
  margin: 0 0 16px;
}

.footer-actions {
  margin-top: 28px;
  padding-bottom: 24px;
  display: flex;
  justify-content: center;
}

@media (max-width: 900px) {
  .pref-card {
    position: static;
    margin-top: 20px;
  }
  .model-row {
    flex-direction: column;
    align-items: stretch;
  }
  .model-select {
    width: 100%;
  }
}
</style>
