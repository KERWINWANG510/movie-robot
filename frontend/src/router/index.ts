import { createRouter, createWebHistory, RouterView } from "vue-router";

import { useAuthStore } from "../stores/auth";
import MainLayout from "../layouts/MainLayout.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import SettingsAiView from "../views/SettingsAiView.vue";
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
          path: "settings",
          component: RouterView,
          redirect: { name: "settings-storage" },
          children: [
            { path: "storage", name: "settings-storage", component: SettingsStorageView },
            { path: "ai", name: "settings-ai", component: SettingsAiView },
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
