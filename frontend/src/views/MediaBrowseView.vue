<script setup lang="ts">
import { Film, Grid, Search, Star, StarFilled, VideoCamera } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";
import "../styles/media-views.css";
import { errMsg } from "../utils/errMsg";

type MediaCard = {
  tmdb_id: number;
  media_type: string;
  title: string;
  poster_path: string;
  poster_url: string;
  overview: string;
  release_date: string;
  vote_average: number;
};

type SubItem = {
  tmdb_id: number;
  media_type: string;
};

type TabKey = "all" | "movie" | "tv";

const router = useRouter();
const tab = ref<TabKey>("all");
const loading = ref(false);
const items = ref<MediaCard[]>([]);
const page = ref(1);
const totalPages = ref(1);
const needKey = ref(false);
const tmdbReady = ref(true);
/** key: `${media_type}:${tmdb_id}` */
const subscribedKeys = ref<Set<string>>(new Set());
const actingKey = ref("");
const searchInput = ref("");
/** 已生效的搜索词；空表示热门/热映/热播列表 */
const activeQuery = ref("");

const isSearchMode = computed(() => Boolean(activeQuery.value.trim()));
const searchPlaceholder = computed(() => {
  if (tab.value === "movie") return "搜索电影名称…";
  if (tab.value === "tv") return "搜索电视剧名称…";
  return "搜索电影或电视剧…";
});
const pageTitle = computed(() => {
  if (isSearchMode.value) {
    if (tab.value === "movie") return "电影搜索结果";
    if (tab.value === "tv") return "电视剧搜索结果";
    return "搜索结果";
  }
  if (tab.value === "movie") return "正在热映";
  if (tab.value === "tv") return "正在热播";
  return "今日热门";
});
const emptyHint = computed(() =>
  isSearchMode.value ? `未找到与「${activeQuery.value}」相关的结果` : "暂无数据",
);
const resultCountLabel = computed(() => {
  if (loading.value || needKey.value) return "";
  if (!items.value.length) return "";
  if (totalPages.value <= 1) return `${items.value.length} 部`;
  return `第 ${page.value} / ${totalPages.value} 页`;
});

function subKey(mediaType: string, tmdbId: number): string {
  return `${mediaType}:${tmdbId}`;
}

function isSubscribed(item: MediaCard): boolean {
  return subscribedKeys.value.has(subKey(item.media_type, item.tmdb_id));
}

async function checkTmdbReady() {
  try {
    const { data } = await http.get<{ tmdb_api_key_saved_in_db: boolean }>("/settings");
    tmdbReady.value = Boolean(data.tmdb_api_key_saved_in_db);
    needKey.value = !tmdbReady.value;
  } catch {
    tmdbReady.value = true;
  }
}

async function loadSubscriptions() {
  try {
    const { data } = await http.get<{ items: SubItem[] }>("/media/subscriptions");
    const next = new Set<string>();
    for (const row of data.items ?? []) {
      next.add(subKey(row.media_type, row.tmdb_id));
    }
    subscribedKeys.value = next;
  } catch {
    /* 列表仍可浏览，订阅状态稍后重试 */
  }
}

async function loadList() {
  if (!tmdbReady.value) {
    items.value = [];
    return;
  }
  loading.value = true;
  needKey.value = false;
  try {
    const q = activeQuery.value.trim();
    let data: { items: MediaCard[]; page: number; total_pages: number };
    if (q) {
      const res = await http.get<{
        items: MediaCard[];
        page: number;
        total_pages: number;
      }>("/media/search", {
        params: { q, media_type: tab.value, page: page.value },
      });
      data = res.data;
    } else {
      const path =
        tab.value === "movie"
          ? "/media/movies/now-playing"
          : tab.value === "tv"
            ? "/media/tv/on-the-air"
            : "/media/trending";
      const res = await http.get<{
        items: MediaCard[];
        page: number;
        total_pages: number;
      }>(path, { params: { page: page.value } });
      data = res.data;
    }
    items.value = data.items ?? [];
    page.value = data.page ?? 1;
    totalPages.value = Math.max(1, data.total_pages ?? 1);
  } catch (e: unknown) {
    items.value = [];
    const msg = errMsg(e);
    if (msg.includes("TMDB API Key") || msg.includes("填写并保存")) {
      needKey.value = true;
      tmdbReady.value = false;
    } else {
      ElMessage.error(msg);
    }
  } finally {
    loading.value = false;
  }
}

function openDetail(item: MediaCard) {
  void router.push({
    name: "media-detail",
    params: { type: item.media_type, id: String(item.tmdb_id) },
  });
}

async function toggleSubscribe(item: MediaCard, ev: Event) {
  ev.stopPropagation();
  ev.preventDefault();
  const key = subKey(item.media_type, item.tmdb_id);
  if (actingKey.value) return;
  actingKey.value = key;
  const next = new Set(subscribedKeys.value);
  try {
    if (next.has(key)) {
      await http.delete(`/media/subscriptions/${item.media_type}/${item.tmdb_id}`);
      next.delete(key);
      subscribedKeys.value = next;
      ElMessage.success("已取消想看");
    } else {
      await http.post("/media/subscriptions", {
        media_type: item.media_type,
        tmdb_id: item.tmdb_id,
      });
      next.add(key);
      subscribedKeys.value = next;
      ElMessage.success("已加入想看");
    }
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    actingKey.value = "";
  }
}

function submitSearch() {
  const q = searchInput.value.trim();
  activeQuery.value = q;
  page.value = 1;
  void loadList();
}

function clearSearch() {
  searchInput.value = "";
  if (!activeQuery.value) return;
  activeQuery.value = "";
  page.value = 1;
  void loadList();
}

function onTabChange() {
  page.value = 1;
  void loadList();
}

function onPageChange(p: number) {
  page.value = p;
  void loadList();
}

onMounted(async () => {
  await checkTmdbReady();
  await Promise.all([loadList(), loadSubscriptions()]);
});
</script>

<template>
  <div class="media-page-wrap media-discover" v-loading="loading">
    <section class="media-discover-hero" aria-label="影视发现">
      <div class="media-discover-hero__mesh" aria-hidden="true" />

      <div class="media-search-bar">
        <div class="media-search-shell">
          <el-input
            v-model="searchInput"
            clearable
            maxlength="200"
            size="large"
            :placeholder="searchPlaceholder"
            class="media-search-input"
            @keyup.enter="submitSearch"
            @clear="clearSearch"
          >
            <template #prefix>
              <el-icon class="media-search-ic"><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" class="media-search-btn" @click="submitSearch">搜索</el-button>
        </div>
        <el-button
          v-if="isSearchMode"
          class="media-search-reset"
          plain
          @click="clearSearch"
        >
          清除搜索
        </el-button>
      </div>

      <div class="media-toolbar">
        <el-radio-group v-model="tab" class="media-seg" @change="onTabChange">
          <el-radio-button value="all">
            <span class="tab-label"><el-icon><Grid /></el-icon> 全部</span>
          </el-radio-button>
          <el-radio-button value="movie">
            <span class="tab-label"><el-icon><Film /></el-icon> 电影</span>
          </el-radio-button>
          <el-radio-button value="tv">
            <span class="tab-label"><el-icon><VideoCamera /></el-icon> 电视剧</span>
          </el-radio-button>
        </el-radio-group>
        <div class="media-toolbar__meta">
          <span class="media-section-chip">{{ pageTitle }}</span>
          <span v-if="isSearchMode" class="media-section-query">「{{ activeQuery }}」</span>
          <span v-if="resultCountLabel" class="media-section-count">{{ resultCountLabel }}</span>
        </div>
      </div>
    </section>

    <section class="media-discover-body" aria-live="polite">
      <div v-if="needKey" class="media-empty-hint media-empty-hint--panel">
        <p class="media-empty-hint__title">尚未配置 TMDB API Key</p>
        <p class="media-empty-hint__text">配置后即可加载热映、热播与搜索结果。</p>
        <el-button type="primary" @click="router.push({ name: 'settings-media' })">
          前往影视数据源配置
        </el-button>
      </div>

      <div v-else-if="!loading && items.length === 0" class="media-empty-hint media-empty-hint--panel">
        <p class="media-empty-hint__title">{{ emptyHint }}</p>
        <p v-if="isSearchMode" class="media-empty-hint__text">试试更短的关键词，或切换全部分类。</p>
        <el-button v-if="isSearchMode" plain @click="clearSearch">返回列表</el-button>
      </div>

      <div v-else class="media-card-grid">
        <article
          v-for="(item, idx) in items"
          :key="`${item.media_type}-${item.tmdb_id}`"
          class="media-card"
          :style="{ '--card-i': String(idx % 10) }"
          role="button"
          tabindex="0"
          :aria-label="item.title"
          @click="openDetail(item)"
          @keydown.enter="openDetail(item)"
        >
          <div class="media-card__poster-wrap">
            <img
              v-if="item.poster_url"
              class="media-card__poster"
              :src="item.poster_url"
              :alt="item.title"
              loading="lazy"
            />
            <div v-else class="media-card__poster-ph">无海报</div>
            <span
              v-if="tab === 'all'"
              class="media-card__type-badge"
              :class="item.media_type === 'tv' ? 'is-tv' : 'is-movie'"
            >
              {{ item.media_type === "tv" ? "电视剧" : "电影" }}
            </span>
            <button
              type="button"
              class="media-card__wish"
              :class="{ 'is-on': isSubscribed(item) }"
              :disabled="actingKey === subKey(item.media_type, item.tmdb_id)"
              :title="isSubscribed(item) ? '取消想看' : '加入想看'"
              :aria-label="isSubscribed(item) ? '取消想看' : '加入想看'"
              @click="toggleSubscribe(item, $event)"
            >
              <el-icon :size="18">
                <StarFilled v-if="isSubscribed(item)" />
                <Star v-else />
              </el-icon>
            </button>
            <span v-if="item.vote_average" class="media-card__score-badge">
              ★ {{ item.vote_average.toFixed(1) }}
            </span>
            <div class="media-card__caption">
              <h3 class="media-card__title">{{ item.title }}</h3>
              <div class="media-card__meta">
                <span v-if="item.release_date" class="media-card__date">{{ item.release_date }}</span>
                <span v-else class="media-card__date">日期未知</span>
              </div>
              <p v-if="item.overview" class="media-card__overview">{{ item.overview }}</p>
            </div>
          </div>
        </article>
      </div>

      <div v-if="!needKey && totalPages > 1" class="media-pager">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="totalPages * 20"
          :page-size="20"
          :current-page="page"
          @current-change="onPageChange"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
