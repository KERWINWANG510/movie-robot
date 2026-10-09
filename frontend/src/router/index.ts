import { createRouter, createWebHistory, RouterView } from "vue-router";

import { useAuthStore } from "../stores/auth";
import MainLayout from "../layouts/MainLayout.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import MediaBrowseView from "../views/MediaBrowseView.vue";
import MediaDetailView from "../views/MediaDetailView.vue";
import MediaSubscriptionsView from "../views/MediaSubscriptionsView.vue";
import SettingsAiView from "../views/SettingsAiView.vue";
import SettingsMediaView from "../views/SettingsMediaView.vue";
import SettingsOpenApiView from "../views/SettingsOpenApiView.vue";
import SettingsStorageView from "../views/SettingsStorageView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import TransferView from "../views/TransferView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    {
      path: "/",
      component: MainLayout,
      children: [
        { path: "", redirect: "/files" },
        {
          path: "files",
          component: RouterView,
          redirect: { name: "rename" },
          children: [
            { path: "", name: "rename", component: HomeView },
            { path: "merge", name: "folder-merge", component: HomeView },
            { path: "transfer", name: "transfer", component: TransferView },
          ],
        },
        {
          path: "media",
          component: RouterView,
          redirect: { name: "media-browse" },
          children: [
            { path: "", name: "media-browse", component: MediaBrowseView },
            {
              path: "subscriptions",
              name: "media-subscriptions",
              component: MediaSubscriptionsView,
            },
            {
              path: ":type/:id",
              name: "media-detail",
              component: MediaDetailView,
            },
          ],
        },
        {
          path: "settings",
          component: RouterView,
          redirect: { name: "settings-storage" },
          children: [
            { path: "storage", name: "settings-storage", component: SettingsStorageView },
            { path: "ai", name: "settings-ai", component: SettingsAiView },
            { path: "media", name: "settings-media", component: SettingsMediaView },
            { path: "open-api", name: "settings-open-api", component: SettingsOpenApiView },
          ],
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: NotFoundView,
      meta: { public: true },
    },
  ],
});

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore();
  if (to.meta.public) {
    if (to.name === "login") {
      await auth.fetchMe().catch(() => undefined);
      if (auth.user) {
        next({ name: "rename" });
        return;
      }
    }
    next();
    return;
  }

  await auth.fetchMe().catch(() => undefined);
  if (!auth.user) {
    next({ name: "login", query: { redirect: to.fullPath } });
    return;
  }
  next();
});

export default router;
