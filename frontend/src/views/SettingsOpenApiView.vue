<script setup lang="ts">
import { Connection, CopyDocument, Key, Link } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

import http from "../api/http";
import "../styles/settings-views.css";
import { useBrowsePrefsStore } from "../stores/browsePrefs";
import { settingsErrMsg } from "../utils/settingsHttp";

type ApiToken = {
  id: number;
  name: string;
  token_prefix: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  expired: boolean;
};

type CatalogParam = {
  name: string;
  location: string;
  type?: string;
  required: boolean;
  description: string;
  example: unknown;
};

type CatalogField = {
  name: string;
  type: string;
  required: boolean;
  description: string;
  example: unknown;
  children?: CatalogField[];
};

type CatalogEndpoint = {
  id: string;
  method: string;
  path: string;
  summary: string;
  description: string;
  notes?: string[];
  headers?: CatalogParam[];
  query_params: CatalogParam[];
  path_params?: CatalogParam[];
  request_fields?: CatalogField[];
  response_fields?: CatalogField[];
  body_example: unknown;
  response_example: unknown;
  error_codes?: string[];
};

type Catalog = {
  base_path: string;
  auth: string;
  auth_notes?: string[];
  endpoints: CatalogEndpoint[];
};

type FlatFieldRow = {
  name: string;
  type: string;
  required: boolean;
  description: string;
  exampleText: string;
};

const router = useRouter();
const prefs = useBrowsePrefsStore();
const returnTo = computed(() => prefs.returnTo);

function goBackToFiles() {
  const target = prefs.returnTo || "/files";
  prefs.setReturnTo(null);
  void router.push(target);
}

const loading = ref(true);
const tokens = ref<ApiToken[]>([]);
const catalog = ref<Catalog | null>(null);
const creating = ref(false);
const newTokenName = ref("");
/** null 表示永久有效 */
const newTokenExpiresDays = ref<number | null>(null);
const plainTokenShown = ref("");
const plainDialogOpen = ref(false);

const expiresOptions = [
  { label: "永久有效", value: null as number | null },
  { label: "7 天", value: 7 },
  { label: "30 天", value: 30 },
  { label: "90 天", value: 90 },
  { label: "365 天", value: 365 },
];

const debugEndpointId = ref("");
const debugToken = ref(localStorage.getItem("mr_open_api_debug_token") || "");
const debugQueryPath = ref("");
/** 路径参数名 → 填写值 */
const debugPathParams = ref<Record<string, string>>({});
const debugBody = ref("");
const debugLoading = ref(false);
const debugStatus = ref<number | null>(null);
const debugResponse = ref("");

const activeTokens = computed(() => tokens.value.filter((t) => !t.revoked_at && !t.expired));
const selectedEndpoint = computed(
  () => catalog.value?.endpoints.find((e) => e.id === debugEndpointId.value) ?? null,
);

function tokenStatus(row: ApiToken): { text: string; type: "success" | "info" | "warning" } {
  if (row.revoked_at) return { text: "已吊销", type: "info" };
  if (row.expired) return { text: "已过期", type: "warning" };
  return { text: "有效", type: "success" };
}

function fmtExpires(row: ApiToken) {
  if (!row.expires_at) return "永久";
  return fmtTime(row.expires_at);
}

watch(debugToken, (v) => {
  localStorage.setItem("mr_open_api_debug_token", v);
});

watch(selectedEndpoint, (ep) => {
  if (!ep) return;
  const pathParam = ep.query_params.find((p) => p.name === "path");
  debugQueryPath.value =
    pathParam && pathParam.example != null ? String(pathParam.example) : "";
  const nextPath: Record<string, string> = {};
  for (const p of ep.path_params || []) {
    nextPath[p.name] = p.example != null ? String(p.example) : "";
  }
  debugPathParams.value = nextPath;
  debugBody.value = ep.body_example != null ? JSON.stringify(ep.body_example, null, 2) : "";
  debugStatus.value = null;
  debugResponse.value = "";
});

function fmtTime(v: string | null) {
  if (!v) return "—";
  try {
    return new Date(v.endsWith("Z") ? v : v + "Z").toLocaleString();
  } catch {
    return v;
  }
}

function methodTagType(method: string) {
  const m = method.toUpperCase();
  if (m === "GET") return "success";
  if (m === "POST") return "warning";
  if (m === "DELETE") return "danger";
  return "info";
}

function exampleText(v: unknown): string {
  if (v === undefined) return "—";
  if (v === null) return "null";
  if (typeof v === "string") return v === "" ? '""' : v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function flattenFields(fields: CatalogField[] | undefined, prefix = ""): FlatFieldRow[] {
  if (!fields?.length) return [];
  const rows: FlatFieldRow[] = [];
  for (const f of fields) {
    const name = prefix ? `${prefix}.${f.name}` : f.name;
    rows.push({
      name,
      type: f.type,
      required: f.required,
      description: f.description,
      exampleText: exampleText(f.example),
    });
    if (f.children?.length) {
      const childPrefix = f.type.startsWith("array") ? `${name}[]` : name;
      rows.push(...flattenFields(f.children, childPrefix));
    }
  }
  return rows;
}

async function loadAll() {
  loading.value = true;
  try {
    const [tokRes, catRes] = await Promise.all([
      http.get<{ items: ApiToken[] }>("/settings/api-tokens"),
      http.get<Catalog>("/settings/open-api/catalog"),
    ]);
    tokens.value = tokRes.data.items ?? [];
    catalog.value = catRes.data;
    if (!debugEndpointId.value && catRes.data.endpoints[0]) {
      debugEndpointId.value = catRes.data.endpoints[0].id;
    }
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    loading.value = false;
  }
}

async function createToken() {
  const name = newTokenName.value.trim();
  if (!name) {
    ElMessage.warning("请填写令牌名称");
    return;
  }
  creating.value = true;
  try {
    const body: { name: string; expires_in_days?: number } = { name };
    if (newTokenExpiresDays.value != null) {
      body.expires_in_days = newTokenExpiresDays.value;
    }
    const { data } = await http.post<{ token: ApiToken; plain_token: string }>("/settings/api-tokens", body);
    plainTokenShown.value = data.plain_token;
    plainDialogOpen.value = true;
    newTokenName.value = "";
    newTokenExpiresDays.value = null;
    if (!debugToken.value) debugToken.value = data.plain_token;
    await loadAll();
    ElMessage.success("令牌已创建，请立即复制保存");
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  } finally {
    creating.value = false;
  }
}

async function copyPlain() {
  try {
    await navigator.clipboard.writeText(plainTokenShown.value);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.warning("复制失败，请手动选中复制");
  }
}

async function revokeToken(row: ApiToken) {
  try {
    await ElMessageBox.confirm(`确定吊销令牌「${row.name}」？吊销后不可恢复。`, "吊销令牌", {
      type: "warning",
      confirmButtonText: "吊销",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await http.delete(`/settings/api-tokens/${row.id}`);
    ElMessage.success("已吊销");
    await loadAll();
  } catch (e: unknown) {
    ElMessage.error(settingsErrMsg(e));
  }
}

function useTokenForDebug(row: ApiToken) {
  ElMessage.info(`令牌明文仅创建时可见。请将此前保存的完整 Key（前缀 ${row.token_prefix}…）粘贴到调试区。`);
}

async function runDebug() {
  const ep = selectedEndpoint.value;
  if (!ep) {
    ElMessage.warning("请选择接口");
    return;
  }
  const token = debugToken.value.trim();
  if (!token) {
    ElMessage.warning("请填写 API Key");
    return;
  }

  const method = ep.method.toUpperCase();
  let body: unknown = undefined;
  if (method === "POST" || method === "PUT" || method === "PATCH") {
    const raw = debugBody.value.trim();
    if (raw) {
      try {
        body = JSON.parse(raw);
      } catch {
        ElMessage.error("请求体不是合法 JSON");
        return;
      }
    }
  }

  debugLoading.value = true;
  debugStatus.value = null;
  debugResponse.value = "";
  try {
    let path = ep.path;
    for (const p of ep.path_params || []) {
      const val = (debugPathParams.value[p.name] ?? "").trim();
      if (p.required && !val) {
        ElMessage.warning(`请填写路径参数 ${p.name}`);
        debugLoading.value = false;
        return;
      }
      path = path.replace(`{${p.name}}`, encodeURIComponent(val));
    }
    if (path.includes("{")) {
      ElMessage.warning("路径中仍有未替换的占位符，请检查路径参数");
      debugLoading.value = false;
      return;
    }
    const url = new URL(path, window.location.origin);
    if (method === "GET" && ep.query_params.some((p) => p.name === "path")) {
      url.searchParams.set("path", debugQueryPath.value);
    }
    const res = await axios.request({
      url: url.pathname + url.search,
      method: ep.method,
      data: body,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      validateStatus: () => true,
      timeout: 120_000,
    });
    debugStatus.value = res.status;
    debugResponse.value =
      typeof res.data === "string" ? res.data : JSON.stringify(res.data, null, 2);
  } catch (e: unknown) {
    debugStatus.value = null;
    debugResponse.value = settingsErrMsg(e);
    ElMessage.error(settingsErrMsg(e));
  } finally {
    debugLoading.value = false;
  }
}

onMounted(() => {
  void loadAll();
});
</script>

<template>
  <div class="settings-page-wrap open-api-page" v-loading="loading">
    <div class="page-head mr-page-intro">
      <h1 class="mr-page-title">开放接口</h1>
      <p class="mr-page-desc">
        供外部系统（如下载器）通过 API Key 调用合并、重命名、传输、想看列表等能力。鉴权方式：{{ catalog?.auth || "Bearer / X-Api-Key" }}
      </p>
    </div>

    <el-card class="block-card" shadow="never">
      <template #header>
        <div class="card-head mr-card-head">
          <el-icon class="head-ic"><Key /></el-icon>
          <span>访问令牌</span>
        </div>
      </template>
      <div class="token-create-row">
        <el-input v-model="newTokenName" placeholder="令牌名称，例如：下载器回调" clearable class="token-name" />
        <el-select v-model="newTokenExpiresDays" placeholder="有效期" class="token-expires">
          <el-option
            v-for="opt in expiresOptions"
            :key="String(opt.value)"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-button type="primary" :loading="creating" @click="createToken">创建令牌</el-button>
      </div>
      <el-table :data="tokens" size="small" empty-text="暂无令牌" class="token-table">
        <el-table-column label="名称" prop="name" min-width="120" />
        <el-table-column label="前缀" min-width="100">
          <template #default="{ row }">
            <code>{{ row.token_prefix }}…</code>
          </template>
        </el-table-column>
        <el-table-column label="有效期" min-width="150">
          <template #default="{ row }">{{ fmtExpires(row) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="150">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最近使用" min-width="150">
          <template #default="{ row }">{{ fmtTime(row.last_used_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="tokenStatus(row).type" size="small">
              {{ tokenStatus(row).text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.revoked_at" link type="primary" @click="useTokenForDebug(row)">调试说明</el-button>
            <el-button v-if="!row.revoked_at" link type="danger" @click="revokeToken(row)">吊销</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p v-if="activeTokens.length === 0" class="hint">至少创建一个有效令牌后，外部系统才能调用开放接口。</p>
    </el-card>

    <el-card class="block-card mt" shadow="never">
      <template #header>
        <div class="card-head mr-card-head">
          <el-icon class="head-ic"><Link /></el-icon>
          <span>接口清单</span>
        </div>
      </template>
      <div v-if="catalog?.auth_notes?.length" class="auth-notes">
        <div class="ep-label">鉴权与通用约定</div>
        <ul>
          <li v-for="(n, i) in catalog.auth_notes" :key="i">{{ n }}</li>
        </ul>
      </div>
      <el-collapse v-if="catalog">
        <el-collapse-item v-for="ep in catalog.endpoints" :key="ep.id" :name="ep.id">
          <template #title>
            <div class="ep-title">
              <el-tag :type="methodTagType(ep.method)" size="small" effect="dark">{{ ep.method }}</el-tag>
              <code class="ep-path">{{ ep.path }}</code>
              <span class="ep-summary">{{ ep.summary }}</span>
            </div>
          </template>
          <p class="ep-desc">{{ ep.description }}</p>
          <ul v-if="ep.notes?.length" class="ep-notes">
            <li v-for="(n, i) in ep.notes" :key="i">{{ n }}</li>
          </ul>

          <div v-if="ep.headers?.length" class="ep-block">
            <div class="ep-label">请求头</div>
            <el-table :data="ep.headers" size="small" border class="field-table">
              <el-table-column label="名称" prop="name" min-width="120" />
              <el-table-column label="类型" prop="type" width="90" />
              <el-table-column label="必填" width="64">
                <template #default="{ row }">{{ row.required ? "是" : "否" }}</template>
              </el-table-column>
              <el-table-column label="说明" prop="description" min-width="200" />
              <el-table-column label="示例" min-width="140" show-overflow-tooltip>
                <template #default="{ row }">{{ exampleText(row.example) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <div v-if="ep.query_params.length" class="ep-block">
            <div class="ep-label">Query 参数</div>
            <el-table :data="ep.query_params" size="small" border class="field-table">
              <el-table-column label="名称" prop="name" min-width="100" />
              <el-table-column label="类型" width="90">
                <template #default="{ row }">{{ row.type || "string" }}</template>
              </el-table-column>
              <el-table-column label="必填" width="64">
                <template #default="{ row }">{{ row.required ? "是" : "否" }}</template>
              </el-table-column>
              <el-table-column label="说明" prop="description" min-width="220" />
              <el-table-column label="示例" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ exampleText(row.example) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <div v-if="ep.path_params?.length" class="ep-block">
            <div class="ep-label">路径参数</div>
            <el-table :data="ep.path_params" size="small" border class="field-table">
              <el-table-column label="名称" prop="name" min-width="100" />
              <el-table-column label="类型" width="90">
                <template #default="{ row }">{{ row.type || "string" }}</template>
              </el-table-column>
              <el-table-column label="必填" width="64">
                <template #default="{ row }">{{ row.required ? "是" : "否" }}</template>
              </el-table-column>
              <el-table-column label="说明" prop="description" min-width="220" />
              <el-table-column label="示例" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ exampleText(row.example) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <div v-if="flattenFields(ep.request_fields).length" class="ep-block">
            <div class="ep-label">请求体字段</div>
            <el-table :data="flattenFields(ep.request_fields)" size="small" border class="field-table" row-key="name">
              <el-table-column label="字段" prop="name" min-width="160" />
              <el-table-column label="类型" prop="type" width="120" />
              <el-table-column label="必填" width="64">
                <template #default="{ row }">{{ row.required ? "是" : "否" }}</template>
              </el-table-column>
              <el-table-column label="说明" prop="description" min-width="220" />
              <el-table-column label="示例" prop="exampleText" min-width="140" show-overflow-tooltip />
            </el-table>
          </div>

          <div v-if="flattenFields(ep.response_fields).length" class="ep-block">
            <div class="ep-label">响应字段</div>
            <el-table :data="flattenFields(ep.response_fields)" size="small" border class="field-table" row-key="name">
              <el-table-column label="字段" prop="name" min-width="160" />
              <el-table-column label="类型" prop="type" width="120" />
              <el-table-column label="必填" width="64">
                <template #default="{ row }">{{ row.required ? "是" : "否" }}</template>
              </el-table-column>
              <el-table-column label="说明" prop="description" min-width="220" />
              <el-table-column label="示例" prop="exampleText" min-width="140" show-overflow-tooltip />
            </el-table>
          </div>

          <div v-if="ep.error_codes?.length" class="ep-block">
            <div class="ep-label">常见错误</div>
            <ul class="ep-notes">
              <li v-for="(e, i) in ep.error_codes" :key="i">{{ e }}</li>
            </ul>
          </div>

          <div v-if="ep.body_example != null" class="ep-block">
            <div class="ep-label">请求示例</div>
            <pre class="code-block">{{ JSON.stringify(ep.body_example, null, 2) }}</pre>
          </div>
          <div v-if="ep.response_example != null" class="ep-block">
            <div class="ep-label">响应示例</div>
            <pre class="code-block">{{ JSON.stringify(ep.response_example, null, 2) }}</pre>
          </div>
          <el-button size="small" type="primary" plain @click="debugEndpointId = ep.id">在调试区打开</el-button>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <el-card class="block-card mt" shadow="never">
      <template #header>
        <div class="card-head mr-card-head">
          <el-icon class="head-ic"><Connection /></el-icon>
          <span>在线调试</span>
        </div>
      </template>
      <el-form label-position="top" class="nice-form debug-form">
        <el-form-item label="选择接口">
          <el-select v-model="debugEndpointId" filterable class="full-width">
            <el-option
              v-for="ep in catalog?.endpoints || []"
              :key="ep.id"
              :label="`${ep.method} ${ep.path} — ${ep.summary}`"
              :value="ep.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="debugToken"
            type="password"
            show-password
            placeholder="粘贴完整令牌（创建时复制的明文）"
            clearable
          />
        </el-form-item>
        <el-form-item
          v-if="selectedEndpoint?.method === 'GET' && selectedEndpoint.query_params.some((p) => p.name === 'path')"
          label="path（相对挂载根）"
        >
          <el-input v-model="debugQueryPath" placeholder="留空为根目录" clearable />
        </el-form-item>
        <template v-if="selectedEndpoint?.path_params?.length">
          <el-form-item
            v-for="p in selectedEndpoint.path_params"
            :key="p.name"
            :label="`路径参数 ${p.name}`"
          >
            <el-input
              v-model="debugPathParams[p.name]"
              :placeholder="p.example != null ? String(p.example) : p.description"
              clearable
            />
          </el-form-item>
        </template>
        <el-form-item
          v-if="
            selectedEndpoint &&
            ['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method.toUpperCase())
          "
          label="请求体 JSON"
        >
          <el-input v-model="debugBody" type="textarea" :rows="10" class="mono-area" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="debugLoading" @click="runDebug">发送请求</el-button>
        </el-form-item>
        <el-form-item v-if="debugStatus != null || debugResponse" label="响应">
          <div class="debug-meta">
            <el-tag v-if="debugStatus != null" :type="debugStatus < 400 ? 'success' : 'danger'" size="small">
              HTTP {{ debugStatus }}
            </el-tag>
          </div>
          <pre class="code-block response-block">{{ debugResponse }}</pre>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="mr-sticky-actionbar">
      <div class="mr-sticky-actionbar__inner">
        <el-button v-if="returnTo" size="large" @click="goBackToFiles">返回文件页</el-button>
        <el-button size="large" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <el-dialog v-model="plainDialogOpen" title="请保存 API Key" width="520px" :close-on-click-modal="false">
      <el-alert type="warning" :closable="false" show-icon class="mb-alert">
        明文仅展示一次，关闭后无法再次查看。请立即复制到安全位置。
      </el-alert>
      <el-input :model-value="plainTokenShown" readonly type="textarea" :rows="3" class="mono-area" />
      <template #footer>
        <el-button type="primary" @click="copyPlain">
          <el-icon class="btn-ic"><CopyDocument /></el-icon>
          复制
        </el-button>
        <el-button @click="plainDialogOpen = false">我已保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.open-api-page {
  padding-bottom: 72px;
}

.token-create-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.token-name {
  flex: 1 1 220px;
  max-width: 360px;
}

.token-expires {
  width: 140px;
  flex-shrink: 0;
}

.token-table {
  width: 100%;
}

.ep-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-right: 8px;
}

.ep-path {
  font-size: 13px;
  color: var(--mr-text);
}

.ep-summary {
  font-size: 13px;
  color: var(--mr-text-secondary);
}

.ep-desc {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--mr-text-secondary);
  line-height: 1.6;
}

.ep-notes {
  margin: 0 0 12px;
  padding-left: 1.2em;
  font-size: 13px;
  color: var(--mr-text-secondary);
  line-height: 1.65;
}

.auth-notes {
  margin-bottom: 14px;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-radius: var(--mr-radius-sm);
}

.auth-notes ul {
  margin: 6px 0 0;
  padding-left: 1.2em;
  font-size: 13px;
  color: var(--mr-text-secondary);
  line-height: 1.65;
}

.ep-block {
  margin-bottom: 14px;
}

.ep-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--mr-text-muted);
  margin-bottom: 6px;
}

.field-table {
  width: 100%;
}

.code-block {
  margin: 0;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-radius: var(--mr-radius-sm);
  font-size: 12px;
  line-height: 1.5;
  overflow: auto;
  max-height: 280px;
  white-space: pre-wrap;
  word-break: break-all;
}

.response-block {
  max-height: 420px;
  width: 100%;
}

.full-width {
  width: 100%;
}

.mono-area :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.debug-meta {
  margin-bottom: 8px;
}

.mb-alert {
  margin-bottom: 12px;
}

.btn-ic {
  margin-right: 4px;
  vertical-align: middle;
}

.hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--mr-text-secondary);
}

@media (max-width: 720px) {
  .token-name {
    max-width: none;
  }
}
</style>
