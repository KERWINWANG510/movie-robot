import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";
import MainLayout from "../layouts/MainLayout.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import SettingsView from "../views/SettingsView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    {
      path: "/",
      component: MainLayout,
      children: [
        { path: "", name: "rename", component: HomeView },
        { path: "merge", name: "folder-merge", component: HomeView },
        { path: "settings", name: "settings", component: SettingsView },
      ],
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
