import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/", name: "home", component: HomeView },
  ],
});

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore();
  if (to.meta.public) {
    if (to.name === "login") {
      await auth.fetchMe().catch(() => undefined);
      if (auth.user) {
        next({ name: "home" });
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
