/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Docker / CI 构建时注入，例如 `123-abc12ef` 或完整 git sha */
  readonly VITE_APP_VERSION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

