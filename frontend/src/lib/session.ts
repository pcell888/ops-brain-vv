/** 与 axios 拦截器一致的本地会话键（嵌入 / 企业管理后台传参后写入） */
export const SESSION_KEYS = {
  enterpriseId: 'enterpriseId',
  userToken: 'userToken',
  platformToken: 'platformToken',
  /** 旧版单一 token，仅作 Authorization，无 userToken 时使用 */
  token: 'token',
} as const;

export function clearAuthSession() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(SESSION_KEYS.token);
  localStorage.removeItem(SESSION_KEYS.platformToken);
  localStorage.removeItem(SESSION_KEYS.userToken);
  localStorage.removeItem(SESSION_KEYS.enterpriseId);
}

export function applyEmbedSession(params: {
  projectId: string;
  userToken: string;
  platformToken: string;
}) {
  if (typeof window === 'undefined') return;
  const { projectId, userToken, platformToken } = params;
  localStorage.setItem(SESSION_KEYS.enterpriseId, projectId);
  localStorage.setItem(SESSION_KEYS.userToken, userToken);
  localStorage.setItem(SESSION_KEYS.platformToken, platformToken);
  localStorage.removeItem(SESSION_KEYS.token);
}
