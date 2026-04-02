/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GIT_COMMIT_HASH: string
  readonly VITE_GIT_COMMIT_TIME: string
  readonly VITE_GIT_COMMIT_INFO: string
  readonly VITE_GIT_COMMIT_BRANCH: string
  readonly VITE_GIT_COMMIT_COUNT: string
  readonly VITE_PIPELINE_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
