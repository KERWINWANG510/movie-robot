<script setup lang="ts">
import { ArrowLeft, Star, StarFilled } from "@element-plus/icons-vue";
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

const PERSON_CARD_WIDTH = 104;
const PERSON_GAP = 12;
const SIMILAR_CARD_WIDTH = 140;
const SIMILAR_GAP = 12;

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const acting = ref(false);
const detail = ref<MediaDetail | null>(null);

const castRowRef = ref<HTMLElement | null>(null);
const crewRowRef = ref<HTMLElement | null>(null);
const similarRowRef = ref<HTMLElement | null>(null);
const castVisible = ref(6);
const crewVisible = ref(6);
const similarVisible = ref(5);

const peopleDialogVisible = ref(false);
const peopleDialogTitle = ref("");
const peopleDialogRolePrefix = ref(false);
const peopleDialogList = ref<PersonCredit[]>([]);

const similarDialogVisible = ref(false);

let castObserver: ResizeObserver | null = null;
let crewObserver: ResizeObserver | null = null;
let similarObserver: ResizeObserver | null = null;

const mediaType = computed(() => String(route.params.type || ""));
const tmdbId = computed(() => Number(route.params.id));

const visibleCast = computed(() => (detail.value?.cast ?? []).slice(0, castVisible.value));
const visibleCrew = computed(() => (detail.value?.crew ?? []).slice(0, crewVisible.value));
const visibleSimilar = computed(() => (detail.value?.similar ?? []).slice(0, similarVisible.value));
const castHasMore = computed(() => (detail.value?.cast?.length ?? 0) > castVisible.value);
const crewHasMore = computed(() => (detail.value?.crew?.length ?? 0) > crewVisible.value);
const similarHasMore = computed(() => (detail.value?.similar?.length ?? 0) > similarVisible.value);

function calcVisibleCount(el: HTMLElement | null, cardWidth: number, gap: number, fallback: number): number {
  if (!el) return fallback;
  const width = el.clientWidth;
  if (width <= 0) return fallback;
  const n = Math.floor((width + gap) / (cardWidth + gap));
  return Math.max(2, n);
}

function syncCastVisible() {
  castVisible.value = calcVisibleCount(castRowRef.value, PERSON_CARD_WIDTH, PERSON_GAP, 6);
}

function syncCrewVisible() {
  crewVisible.value = calcVisibleCount(crewRowRef.value, PERSON_CARD_WIDTH, PERSON_GAP, 6);
}

function syncSimilarVisible() {
  similarVisible.value = calcVisibleCount(similarRowRef.value, SIMILAR_CARD_WIDTH, SIMILAR_GAP, 5);
}

function bindRowObservers() {
  castObserver?.disconnect();
  crewObserver?.disconnect();
  similarObserver?.disconnect();
  castObserver = null;
  crewObserver = null;
  similarObserver = null;

  if (typeof ResizeObserver === "undefined") {
    syncCastVisible();
    syncCrewVisible();
    syncSimilarVisible();
    return;
  }

  if (castRowRef.value) {
    castObserver = new ResizeObserver(() => syncCastVisible());
    castObserver.observe(castRowRef.value);
    syncCastVisible();
  }
  if (crewRowRef.value) {
    crewObserver = new ResizeObserver(() => syncCrewVisible());
    crewObserver.observe(crewRowRef.value);
    syncCrewVisible();
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

function openPeopleMore(kind: "cast" | "crew") {
  if (!detail.value) return;
  if (kind === "cast") {
    peopleDialogTitle.value = "全部演员";
    peopleDialogRolePrefix.value = true;
    peopleDialogList.value = detail.value.cast ?? [];
  } else {
    peopleDialogTitle.value = "全部职员";
    peopleDialogRolePrefix.value = false;
    peopleDialogList.value = detail.value.crew ?? [];
  }
  peopleDialogVisible.value = true;
}

function openSimilarMore() {
  similarDialogVisible.value = true;
}

onMounted(loadDetail);
watch(
  () => [route.params.type, route.params.id],
  () => {
    void loadDetail();
  },
);

onBeforeUnmount(() => {
  castObserver?.disconnect();
  crewObserver?.disconnect();
  similarObserver?.disconnect();
});
</script>

<template>
  <div class="media-page-wrap" v-loading="loading">
    <div class="media-toolbar">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div v-if="!loading && !detail" class="media-empty-hint">未找到该条目</div>

    <div v-else-if="detail" class="media-detail">
      <div class="media-detail__poster-wrap">
        <img
          v-if="detail.poster_url"
          class="media-detail__poster"
          :src="detail.poster_url"
          :alt="detail.title"
        />
        <div v-else class="media-card__poster-ph">无海报</div>
      </div>
      <div>
        <h1 class="media-detail__title">{{ detail.title }}</h1>
        <p v-if="detail.original_title && detail.original_title !== detail.title" class="media-detail__sub">
          {{ detail.original_title }}
        </p>
        <div class="media-detail__tags">
          <el-tag size="small" effect="plain">{{ detail.media_type === "tv" ? "电视剧" : "电影" }}</el-tag>
          <el-tag v-if="detail.release_date" size="small" type="info" effect="plain">{{
            detail.release_date
          }}</el-tag>
          <el-tag v-if="detail.vote_average" size="small" type="warning" effect="plain">
            ★ {{ detail.vote_average.toFixed(1) }}
            <span v-if="detail.vote_count">（{{ detail.vote_count }}）</span>
          </el-tag>
          <el-tag v-if="detail.runtime" size="small" effect="plain">{{ detail.runtime }} 分钟</el-tag>
          <el-tag v-for="g in detail.genres" :key="g.id" size="small" effect="plain">{{ g.name }}</el-tag>
        </div>
        <div class="media-detail__actions">
          <el-button
            :type="detail.subscribed ? 'default' : 'primary'"
            :loading="acting"
            @click="toggleSubscribe"
          >
            <el-icon class="btn-ic">
              <StarFilled v-if="detail.subscribed" />
              <Star v-else />
            </el-icon>
            {{ detail.subscribed ? "取消想看" : "加入想看" }}
          </el-button>
          <el-button @click="router.push({ name: 'media-subscriptions' })">查看想看列表</el-button>
        </div>
        <p class="media-detail__overview">{{ detail.overview || "暂无简介" }}</p>
      </div>
    </div>

    <section v-if="detail && detail.cast?.length" class="media-credits">
      <div class="media-credits__head">
        <h2 class="media-credits__title">演员</h2>
        <el-button v-if="castHasMore" text type="primary" @click="openPeopleMore('cast')">更多</el-button>
      </div>
      <div ref="castRowRef" class="media-credits__row">
        <div
          v-for="p in visibleCast"
          :key="`cast-${p.person_id}-${p.role}`"
          class="media-person"
        >
          <img
            v-if="p.profile_url"
            class="media-person__avatar"
            :src="p.profile_url"
            :alt="p.name"
            loading="lazy"
          />
          <div v-else class="media-person__avatar media-person__avatar--ph">无图</div>
          <div class="media-person__name">{{ p.name }}</div>
          <div v-if="p.role" class="media-person__role">饰 {{ p.role }}</div>
        </div>
      </div>
    </section>

    <section v-if="detail && detail.crew?.length" class="media-credits">
      <div class="media-credits__head">
        <h2 class="media-credits__title">职员</h2>
        <el-button v-if="crewHasMore" text type="primary" @click="openPeopleMore('crew')">更多</el-button>
      </div>
      <div ref="crewRowRef" class="media-credits__row">
        <div
          v-for="p in visibleCrew"
          :key="`crew-${p.person_id}-${p.role}`"
          class="media-person"
        >
          <img
            v-if="p.profile_url"
            class="media-person__avatar"
            :src="p.profile_url"
            :alt="p.name"
            loading="lazy"
          />
          <div v-else class="media-person__avatar media-person__avatar--ph">无图</div>
          <div class="media-person__name">{{ p.name }}</div>
          <div v-if="p.role" class="media-person__role">{{ p.role }}</div>
        </div>
      </div>
    </section>

    <section v-if="detail && detail.similar?.length" class="media-credits">
      <div class="media-credits__head">
        <h2 class="media-credits__title">相似推荐</h2>
        <el-button v-if="similarHasMore" text type="primary" @click="openSimilarMore">更多</el-button>
      </div>
      <div ref="similarRowRef" class="media-similar-row">
        <article
          v-for="item in visibleSimilar"
          :key="`similar-${item.media_type}-${item.tmdb_id}`"
          class="media-card media-similar-card"
          role="button"
          tabindex="0"
          @click="openSimilar(item)"
          @keydown.enter="openSimilar(item)"
        >
          <img
            v-if="item.poster_url"
            class="media-card__poster"
            :src="item.poster_url"
            :alt="item.title"
            loading="lazy"
          />
          <div v-else class="media-card__poster-ph">无海报</div>
          <div class="media-card__body">
            <h3 class="media-card__title">{{ item.title }}</h3>
            <div class="media-card__meta">
              <span v-if="item.vote_average" class="media-card__score">★ {{ item.vote_average.toFixed(1) }}</span>
              <span v-if="item.release_date" class="media-card__date">{{ item.release_date }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <el-dialog
      v-model="peopleDialogVisible"
      :title="peopleDialogTitle"
      width="min(920px, 94vw)"
      destroy-on-close
      append-to-body
    >
      <div class="media-credits-dialog__grid">
        <div
          v-for="p in peopleDialogList"
          :key="`more-${p.person_id}-${p.role}`"
          class="media-person"
        >
          <img
            v-if="p.profile_url"
            class="media-person__avatar"
            :src="p.profile_url"
            :alt="p.name"
            loading="lazy"
          />
          <div v-else class="media-person__avatar media-person__avatar--ph">无图</div>
          <div class="media-person__name">{{ p.name }}</div>
          <div v-if="p.role" class="media-person__role">
            {{ peopleDialogRolePrefix ? `饰 ${p.role}` : p.role }}
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog
      v-model="similarDialogVisible"
      title="全部相似推荐"
      width="min(920px, 94vw)"
      destroy-on-close
      append-to-body
    >
      <div class="media-similar-dialog__grid">
        <article
          v-for="item in detail?.similar ?? []"
          :key="`similar-more-${item.media_type}-${item.tmdb_id}`"
          class="media-card"
          role="button"
          tabindex="0"
          @click="openSimilar(item)"
          @keydown.enter="openSimilar(item)"
        >
          <img
            v-if="item.poster_url"
            class="media-card__poster"
            :src="item.poster_url"
            :alt="item.title"
            loading="lazy"
          />
          <div v-else class="media-card__poster-ph">无海报</div>
          <div class="media-card__body">
            <h3 class="media-card__title">{{ item.title }}</h3>
            <div class="media-card__meta">
              <span v-if="item.vote_average" class="media-card__score">★ {{ item.vote_average.toFixed(1) }}</span>
              <span v-if="item.release_date" class="media-card__date">{{ item.release_date }}</span>
            </div>
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
