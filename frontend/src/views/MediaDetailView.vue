<script setup lang="ts">
import {
  ArrowLeft,
  Calendar,
  Clock,
  CollectionTag,
  Document,
  Film,
  Star,
  StarFilled,
  User,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import http from "../api/http";
import "../styles/media-views.css";
import { errMsg } from "../utils/errMsg";

type Genre = { id: number; name: string };

type PersonCredit = {
  person_id: number;
  name: string;
  role: string;
  profile_path: string;
  profile_url: string;
};

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

type MediaDetail = {
  tmdb_id: number;
  media_type: string;
  title: string;
  original_title: string;
  poster_path: string;
  poster_url: string;
  backdrop_path: string;
  backdrop_url: string;
  overview: string;
  release_date: string;
  vote_average: number;
  vote_count: number;
  runtime: number | null;
  genres: Genre[];
  status: string;
  cast: PersonCredit[];
  crew: PersonCredit[];
  similar: MediaCard[];
  subscribed: boolean;
};

const PERSON_CARD_WIDTH = 96;
const PERSON_GAP = 16;
const SIMILAR_CARD_WIDTH = 160;
const SIMILAR_GAP = 14;

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const acting = ref(false);
const detail = ref<MediaDetail | null>(null);

const peopleRowRef = ref<HTMLElement | null>(null);
const similarRowRef = ref<HTMLElement | null>(null);
const peopleVisible = ref(8);
const similarVisible = ref(5);

const peopleDialogVisible = ref(false);
const similarDialogVisible = ref(false);

let peopleObserver: ResizeObserver | null = null;
let similarObserver: ResizeObserver | null = null;

const mediaType = computed(() => String(route.params.type || ""));
const tmdbId = computed(() => Number(route.params.id));

/** 演职员：演员优先，其后职员（去重） */
const peopleCredits = computed(() => {
  if (!detail.value) return [] as (PersonCredit & { kind: "cast" | "crew" })[];
  const seen = new Set<number>();
  const out: (PersonCredit & { kind: "cast" | "crew" })[] = [];
  for (const p of detail.value.cast ?? []) {
    if (seen.has(p.person_id)) continue;
    seen.add(p.person_id);
    out.push({ ...p, kind: "cast" });
  }
  for (const p of detail.value.crew ?? []) {
    if (seen.has(p.person_id)) continue;
    seen.add(p.person_id);
    out.push({ ...p, kind: "crew" });
  }
  return out;
});

const visiblePeople = computed(() => peopleCredits.value.slice(0, peopleVisible.value));
const visibleSimilar = computed(() => (detail.value?.similar ?? []).slice(0, similarVisible.value));
const peopleHasMore = computed(() => peopleCredits.value.length > peopleVisible.value);
const similarHasMore = computed(() => (detail.value?.similar?.length ?? 0) > similarVisible.value);

const displayTitle = computed(() => {
  if (!detail.value) return "";
  const { title, original_title } = detail.value;
  if (original_title && original_title !== title) return `${title} / ${original_title}`;
  return title;
});

const releaseYear = computed(() => {
  const d = detail.value?.release_date;
  if (!d || d.length < 4) return "";
  return d.slice(0, 4);
});

const genreLabel = computed(() => (detail.value?.genres ?? []).map((g) => g.name).join(" · "));

function calcVisibleCount(el: HTMLElement | null, cardWidth: number, gap: number, fallback: number): number {
  if (!el) return fallback;
  const width = el.clientWidth;
  if (width <= 0) return fallback;
  const n = Math.floor((width + gap) / (cardWidth + gap));
  return Math.max(2, n);
}

function syncPeopleVisible() {
  peopleVisible.value = calcVisibleCount(peopleRowRef.value, PERSON_CARD_WIDTH, PERSON_GAP, 8);
}

function syncSimilarVisible() {
  similarVisible.value = calcVisibleCount(similarRowRef.value, SIMILAR_CARD_WIDTH, SIMILAR_GAP, 5);
}

function bindRowObservers() {
  peopleObserver?.disconnect();
  similarObserver?.disconnect();
  peopleObserver = null;
  similarObserver = null;

  if (typeof ResizeObserver === "undefined") {
    syncPeopleVisible();
    syncSimilarVisible();
    return;
  }

  if (peopleRowRef.value) {
    peopleObserver = new ResizeObserver(() => syncPeopleVisible());
    peopleObserver.observe(peopleRowRef.value);
    syncPeopleVisible();
  }
  if (similarRowRef.value) {
    similarObserver = new ResizeObserver(() => syncSimilarVisible());
    similarObserver.observe(similarRowRef.value);
    syncSimilarVisible();
  }
}

async function loadDetail() {
  if (!mediaType.value || !Number.isFinite(tmdbId.value) || tmdbId.value < 1) {
    ElMessage.error("无效的影视条目");
    return;
  }
  loading.value = true;
  try {
    const { data } = await http.get<MediaDetail>(`/media/${mediaType.value}/${tmdbId.value}`);
    detail.value = data;
    await nextTick();
    bindRowObservers();
  } catch (e: unknown) {
    detail.value = null;
    const msg = errMsg(e);
    ElMessage.error(msg);
    if (msg.includes("TMDB API Key") || msg.includes("填写并保存")) {
      void router.push({ name: "settings-media" });
    }
  } finally {
    loading.value = false;
  }
}

async function toggleSubscribe() {
  if (!detail.value) return;
  acting.value = true;
  try {
    if (detail.value.subscribed) {
      await http.delete(`/media/subscriptions/${detail.value.media_type}/${detail.value.tmdb_id}`);
      detail.value.subscribed = false;
      ElMessage.success("已取消想看");
    } else {
      await http.post("/media/subscriptions", {
        media_type: detail.value.media_type,
        tmdb_id: detail.value.tmdb_id,
      });
      detail.value.subscribed = true;
      ElMessage.success("已加入想看");
    }
  } catch (e: unknown) {
    ElMessage.error(errMsg(e));
  } finally {
    acting.value = false;
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    void router.push({ name: "media-browse" });
  }
}

function openSimilar(item: MediaCard) {
  similarDialogVisible.value = false;
  void router.push({
    name: "media-detail",
    params: { type: item.media_type, id: String(item.tmdb_id) },
  });
}

function openPeopleMore() {
  peopleDialogVisible.value = true;
}

function openSimilarMore() {
  similarDialogVisible.value = true;
}

function personRoleText(p: PersonCredit & { kind: "cast" | "crew" }) {
  if (!p.role) return p.kind === "cast" ? "演员" : "职员";
  return p.kind === "cast" ? `饰 ${p.role}` : p.role;
}

onMounted(loadDetail);
watch(
  () => [route.params.type, route.params.id],
  () => {
    void loadDetail();
  },
);

onBeforeUnmount(() => {
  peopleObserver?.disconnect();
  similarObserver?.disconnect();
});
</script>

<template>
  <div class="media-detail-page" v-loading="loading">
    <div v-if="!loading && !detail" class="media-empty-hint">未找到该条目</div>

    <template v-else-if="detail">
      <!-- Hero：全幅 backdrop + 海报 + 元信息 -->
      <header
        class="md-hero"
        :style="
          detail.backdrop_url
            ? { '--detail-backdrop': `url(${detail.backdrop_url})` }
            : undefined
        "
      >
        <div class="md-hero__backdrop" aria-hidden="true" />
        <div class="md-hero__veil" aria-hidden="true" />

        <div class="md-hero__top">
          <button type="button" class="md-back" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回影视发现
          </button>
        </div>

        <div class="md-hero__body">
          <div class="md-poster">
            <img
              v-if="detail.poster_url"
              :src="detail.poster_url"
              :alt="detail.title"
            />
            <div v-else class="md-poster__ph">无海报</div>
          </div>

          <div class="md-hero__info">
            <div class="md-badges">
              <span class="md-badge md-badge--type">
                {{ detail.media_type === "tv" ? "电视剧" : "电影" }}
              </span>
              <span v-if="detail.vote_average" class="md-badge md-badge--score">
                TMDB {{ detail.vote_average.toFixed(1) }}
              </span>
              <span v-if="detail.status" class="md-badge">{{ detail.status }}</span>
            </div>

            <h1 class="md-title">{{ displayTitle }}</h1>

            <p v-if="detail.overview" class="md-hero-synopsis">{{ detail.overview }}</p>

            <div class="md-meta">
              <span v-if="releaseYear" class="md-meta__item">
                <el-icon><Calendar /></el-icon>
                {{ releaseYear }}
              </span>
              <span v-if="detail.runtime" class="md-meta__item">
                <el-icon><Clock /></el-icon>
                {{ detail.runtime }} 分钟
              </span>
              <span v-if="genreLabel" class="md-meta__item">
                <el-icon><Film /></el-icon>
                {{ genreLabel }}
              </span>
              <span v-if="detail.release_date" class="md-meta__item">
                <el-icon><CollectionTag /></el-icon>
                {{ detail.release_date }}
              </span>
            </div>

            <div class="md-actions">
              <el-button
                type="primary"
                size="large"
                class="md-cta"
                :loading="acting"
                @click="toggleSubscribe"
              >
                <el-icon class="btn-ic">
                  <StarFilled v-if="detail.subscribed" />
                  <Star v-else />
                </el-icon>
                {{ detail.subscribed ? "已在想看清单" : "加入想看清单" }}
              </el-button>
              <el-button size="large" plain class="md-cta-ghost" @click="router.push({ name: 'media-subscriptions' })">
                查看想看列表
              </el-button>
            </div>
          </div>
        </div>
      </header>

      <div class="md-body">
        <!-- 剧情简介 -->
        <section class="md-section">
          <div class="md-section__head">
            <el-icon class="md-section__ic"><Document /></el-icon>
            <h2 class="md-section__title">
              剧情简介
              <span class="md-section__en">Overview</span>
            </h2>
          </div>
          <p class="md-overview-text">{{ detail.overview || "暂无简介" }}</p>
        </section>

        <!-- 主要演职员 -->
        <section v-if="peopleCredits.length" class="md-section">
          <div class="md-section__head">
            <el-icon class="md-section__ic"><User /></el-icon>
            <h2 class="md-section__title">
              主要演职员
              <span class="md-section__en">Cast &amp; Crew</span>
            </h2>
            <el-button v-if="peopleHasMore" text type="primary" class="md-more" @click="openPeopleMore">
              更多
            </el-button>
          </div>
          <div ref="peopleRowRef" class="md-people-row">
            <div
              v-for="p in visiblePeople"
              :key="`p-${p.kind}-${p.person_id}-${p.role}`"
              class="md-person"
            >
              <img
                v-if="p.profile_url"
                class="md-person__avatar"
                :src="p.profile_url"
                :alt="p.name"
                loading="lazy"
              />
              <div v-else class="md-person__avatar md-person__avatar--ph">无图</div>
              <div class="md-person__name">{{ p.name }}</div>
              <div class="md-person__role">{{ personRoleText(p) }}</div>
            </div>
          </div>
        </section>

        <!-- 相似推荐 -->
        <section v-if="detail.similar?.length" class="md-section">
          <div class="md-section__head">
            <el-icon class="md-section__ic"><StarFilled /></el-icon>
            <h2 class="md-section__title">
              类似影视作品推荐
              <span class="md-section__en">Recommended</span>
            </h2>
            <el-button v-if="similarHasMore" text type="primary" class="md-more" @click="openSimilarMore">
              更多
            </el-button>
          </div>
          <div ref="similarRowRef" class="md-similar-row">
            <article
              v-for="item in visibleSimilar"
              :key="`similar-${item.media_type}-${item.tmdb_id}`"
              class="md-similar-card"
              role="button"
              tabindex="0"
              @click="openSimilar(item)"
              @keydown.enter="openSimilar(item)"
            >
              <div class="md-similar-card__poster">
                <img
                  v-if="item.poster_url"
                  :src="item.poster_url"
                  :alt="item.title"
                  loading="lazy"
                />
                <div v-else class="md-similar-card__ph">无海报</div>
                <span v-if="item.vote_average" class="md-similar-card__score">
                  ★ {{ item.vote_average.toFixed(1) }}
                </span>
              </div>
              <div class="md-similar-card__body">
                <h3 class="md-similar-card__title">{{ item.title }}</h3>
                <p class="md-similar-card__meta">
                  <span v-if="item.release_date">{{ item.release_date.slice(0, 4) }}</span>
                  <span>{{ item.media_type === "tv" ? "电视剧" : "电影" }}</span>
                </p>
              </div>
            </article>
          </div>
        </section>
      </div>
    </template>

    <el-dialog
      v-model="peopleDialogVisible"
      title="全部演职员"
      width="min(920px, 94vw)"
      destroy-on-close
      append-to-body
    >
      <div class="md-people-dialog">
        <div
          v-for="p in peopleCredits"
          :key="`more-${p.kind}-${p.person_id}-${p.role}`"
          class="md-person"
        >
          <img
            v-if="p.profile_url"
            class="md-person__avatar"
            :src="p.profile_url"
            :alt="p.name"
            loading="lazy"
          />
          <div v-else class="md-person__avatar md-person__avatar--ph">无图</div>
          <div class="md-person__name">{{ p.name }}</div>
          <div class="md-person__role">{{ personRoleText(p) }}</div>
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="similarDialogVisible"
      title="全部相似推荐"
      width="min(960px, 94vw)"
      destroy-on-close
      append-to-body
    >
      <div class="md-similar-dialog">
        <article
          v-for="item in detail?.similar ?? []"
          :key="`similar-more-${item.media_type}-${item.tmdb_id}`"
          class="md-similar-card"
          role="button"
          tabindex="0"
          @click="openSimilar(item)"
          @keydown.enter="openSimilar(item)"
        >
          <div class="md-similar-card__poster">
            <img
              v-if="item.poster_url"
              :src="item.poster_url"
              :alt="item.title"
              loading="lazy"
            />
            <div v-else class="md-similar-card__ph">无海报</div>
            <span v-if="item.vote_average" class="md-similar-card__score">
              ★ {{ item.vote_average.toFixed(1) }}
            </span>
          </div>
          <div class="md-similar-card__body">
            <h3 class="md-similar-card__title">{{ item.title }}</h3>
            <p class="md-similar-card__meta">
              <span v-if="item.release_date">{{ item.release_date.slice(0, 4) }}</span>
              <span>{{ item.media_type === "tv" ? "电视剧" : "电影" }}</span>
            </p>
          </div>
        </article>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.btn-ic {
  margin-right: 4px;
}
</style>
