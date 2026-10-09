<script setup lang="ts">
import { Film, Grid, Search, StarFilled, VideoCamera } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import http from "../api/http";
import "../styles/media-views.css";
import { errMsg } from "../utils/errMsg";

type SubItem = {
  id: number;
  tmdb_id: number;
  media_type: string;
  title: string;
  poster_path: string;
  poster_url: string;
  overview: string;
  release_date: string;
  created_at: string;
};

type TabKey = "all" | "movie" | "tv";

const router = useRouter();
const loading = ref(false);
const items = ref<SubItem[]>([]);
const tab = ref<TabKey>("all");
const searchInput = ref("");
/** 已生效的搜索词 */
const activeQuery = ref("");

const isSearchMode = computed(() => Boolean(activeQuery.value.trim()));

const searchPlaceholder = computed(() => {
  if (tab.value === "movie") return "在想看中搜索电影…";
  if (tab.value === "tv") return "在想看中搜索电视剧…";
  return "在想看中搜索电影或电视剧…";
});

const pageTitle = computed(() => {
  if (isSearchMode.value) {
    if (tab.value === "movie") return "电影搜索结果";
    if (tab.value === "tv") return "电视剧搜索结果";
    return "搜索结果";
  }
  if (tab.value === "movie") return "电影想看";
  if (tab.value === "tv") return "电视剧想看";
  return "想看列表";
});

const filteredItems = computed(() => {
  let list = items.value;
  if (tab.value === "movie" || tab.value === "tv") {
    list = list.filter((x) => x.media_type === tab.value);
  }
  const q = activeQuery.value.trim().toLowerCase();
  if (q) {
    list = list.filter((x) => {
      const title = (x.title || "").toLowerCase();
      const overview = (x.overview || "").toLowerCase();
      return title.includes(q) || overview.includes(q);
    });
  }
  return list;
});

const resultCountLabel = computed(() => {
  if (loading.value) return "";
  const n = filteredItems.value.length;
  if (!n && !items.value.length) return "";
  if (isSearchMode.value || tab.value !== "all") {
    return `${n} / ${items.value.length} 部`;
  }
  if (!n) return "";
  return `${n} 部`;
});

const emptyHint = computed(() => {
  if (!items.value.length) return "暂无想看条目";
  if (isSearchMode.value) return `未找到与「${activeQuery.value}」相关的想看条目`;
  if (tab.value === "movie") return "想看列表中暂无电影";
  if (tab.value === "tv") return "想看列表中暂无电视剧";
  return "暂无数据";
});

async function loadList() {
  loading.value = true;
  try {
    const { data } = await http.get<{ items: SubItem[] }>("/media/subscriptions");
    items.value = data.items ?? [];
  } catch (e: unknown) {
    items.value = [];
    ElMessage.error(errMsg(e));
  } finally {
    loading.value = false;
  }
}

function openDetail(item: SubItem) {
  void router.push({
    name: "media-detail",
    params: { type: item.media_type, id: String(item.tmdb_id) },
  });
}

async function removeItem(item: SubItem, ev: Event) {
  ev.stopPropagation();
  try {
    await ElMessageBox.confirm(`确定将「${item.title}」移出想看列表？`, "取消想看", {
      type: "warning",
      confirmButtonText: "移出",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await http.delete(`/media/subscriptions/${item.media_type}/${item.tmdb_id}`);
    ElMessage.success("已移出想看");
    items.value = items.value.filter((x) => x.id !== item.id);
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  }
}

function submitSearch() {
  activeQuery.value = searchInput.value.trim();
}

function clearSearch() {
  searchInput.value = "";
  activeQuery.value = "";
}

onMounted(loadList);
</script>

<template>
  <div class="media-page-wrap media-wishlist" v-loading="loading">
    <section class="media-discover-hero" aria-label="想看列表">
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
        <el-button
          v-else
          class="media-search-reset"
          plain
          @click="router.push({ name: 'media-browse' })"
        >
          去影视发现
        </el-button>
      </div>

      <div class="media-toolbar">
        <el-radio-group v-model="tab" class="media-seg">
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
      <div v-if="!loading && filteredItems.length === 0" class="media-empty-hint media-empty-hint--panel">
        <p class="media-empty-hint__title">{{ emptyHint }}</p>
        <template v-if="!items.length">
          <p class="media-empty-hint__text">在影视发现页给海报点星，即可加入这里。</p>
          <el-button type="primary" @click="router.push({ name: 'media-browse' })">去影视发现</el-button>
        </template>
        <template v-else>
          <p class="media-empty-hint__text">试试切换分类，或清除搜索条件。</p>
          <el-button v-if="isSearchMode" plain @click="clearSearch">清除搜索</el-button>
          <el-button v-else-if="tab !== 'all'" plain @click="tab = 'all'">查看全部</el-button>
        </template>
      </div>

      <div v-else class="media-card-grid">
        <article
          v-for="(item, idx) in filteredItems"
          :key="item.id"
          class="media-card media-wishlist-card"
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
              class="media-card__wish is-on"
              title="取消想看"
              aria-label="取消想看"
              @click="removeItem(item, $event)"
            >
              <el-icon :size="18"><StarFilled /></el-icon>
            </button>
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
