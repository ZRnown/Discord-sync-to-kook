/**
 * 认证相关工具函数
 */

const AUTH_TOKEN_KEY = "auth_token"
const USER_ROLE_KEY = "user_role"

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(AUTH_TOKEN_KEY, token)
}

export function removeAuthToken(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(USER_ROLE_KEY)
}

export function isAuthenticated(): boolean {
  return getAuthToken() !== null
}

export function getUserRole(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(USER_ROLE_KEY)
}

export function setUserRole(role: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(USER_ROLE_KEY, role)
}

