import { defineStore } from "pinia";
import { ref, watch } from "vue";

const LS_HIDE_DOT = "mr_hide_dotfiles";
const LS_TRANSFER_DEST = "mr_transfer_dest_id";
const LS_TRANSFER_MODE = "mr_transfer_mode";
const LS_SKIP_COPY_CONFIRM = "mr_skip_copy_confirm";
const LS_BROWSE_PATH = "mr_browse_path";
const LS_RETURN_TO = "mr_return_to";
const LS_CHECKLIST_DISMISS = "mr_checklist_dismissed";

function readBool(key: string, fallback: boolean): boolean {
  const v = localStorage.getItem(key);
  if (v === null) return fallback;
  return v === "1" || v === "true";
}

function writeBool(key: string, v: boolean) {
  localStorage.setItem(key, v ? "1" : "0");
}

function readTransferDestId(): number | null {
  const raw = localStorage.getItem(LS_TRANSFER_DEST);
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export const useBrowsePrefsStore = defineStore("browsePrefs", () => {
  const hideDotfiles = ref(readBool(LS_HIDE_DOT, true));
  const skipCopyConfirm = ref(readBool(LS_SKIP_COPY_CONFIRM, false));
  const checklistDismissed = ref(readBool(LS_CHECKLIST_DISMISS, false));

  const transferMode = ref<"copy" | "move">(
    localStorage.getItem(LS_TRANSFER_MODE) === "move" ? "move" : "copy",
  );

  const savedTransferDestId = ref<number | null>(readTransferDestId());

  watch(hideDotfiles, (v) => writeBool(LS_HIDE_DOT, v));
  watch(skipCopyConfirm, (v) => writeBool(LS_SKIP_COPY_CONFIRM, v));
  watch(checklistDismissed, (v) => writeBool(LS_CHECKLIST_DISMISS, v));
  watch(transferMode, (v) => localStorage.setItem(LS_TRANSFER_MODE, v));
  watch(savedTransferDestId, (v) => {
    if (v == null) localStorage.removeItem(LS_TRANSFER_DEST);
    else localStorage.setItem(LS_TRANSFER_DEST, String(v));
  });

  function getSavedBrowsePath(): string {
    return localStorage.getItem(LS_BROWSE_PATH) ?? "";
  }

  function setSavedBrowsePath(path: string) {
    localStorage.setItem(LS_BROWSE_PATH, path);
  }

  const returnTo = ref<string | null>(localStorage.getItem(LS_RETURN_TO));

  function getReturnTo(): string | null {
    return returnTo.value;
  }

  function setReturnTo(fullPath: string | null) {
    returnTo.value = fullPath;
    if (!fullPath) localStorage.removeItem(LS_RETURN_TO);
    else localStorage.setItem(LS_RETURN_TO, fullPath);
  }

  return {
    hideDotfiles,
    skipCopyConfirm,
    checklistDismissed,
    transferMode,
    savedTransferDestId,
    returnTo,
    getSavedBrowsePath,
    setSavedBrowsePath,
    getReturnTo,
    setReturnTo,
  };
});
