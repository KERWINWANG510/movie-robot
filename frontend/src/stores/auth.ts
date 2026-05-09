import { defineStore } from "pinia";
import { ref } from "vue";

import http from "../api/http";

export type UserMe = {
  id: number;
  username: string;
  auto_rename_without_preview: boolean;
};

export const useAuthStore = defineStore("auth", () => {
  const user = ref<UserMe | null>(null);

  async function fetchMe() {
    const { data } = await http.get<UserMe>("/auth/me");
    user.value = data;
    return data;
  }

  async function login(username: string, password: string) {
    const { data } = await http.post<UserMe>("/auth/login", { username, password });
    user.value = data;
    return data;
  }

  async function logout() {
    await http.post("/auth/logout");
    user.value = null;
  }

  async function register(username: string, password: string) {
    const { data } = await http.post<UserMe>("/auth/register", { username, password });
    user.value = data;
    return data;
  }

  async function updatePreference(auto_rename_without_preview: boolean) {
    const { data } = await http.patch<UserMe>("/users/me/preference", {
      auto_rename_without_preview,
    });
    user.value = data;
    return data;
  }

  return { user, fetchMe, login, logout, register, updatePreference };
});
