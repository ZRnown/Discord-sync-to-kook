"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { getAuthToken, setAuthToken, removeAuthToken, isAuthenticated } from "@/lib/auth"
import { API_BASE_URL } from "@/lib/api-config"

interface LoginCredentials {
  username: string
  password: string
}

interface ChangePasswordData {
  old_password: string
  new_password: string
}

export function useAuth() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const login = async (credentials: LoginCredentials) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(credentials),
      })

      const data = await response.json()

      if (data.success && data.token) {
        setAuthToken(data.token)
        router.push("/")
        return { success: true }
      } else {
        setError(data.message || "登录失败")
        return { success: false, error: data.message || "登录失败" }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "登录失败"
      setError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    const token = getAuthToken()
    if (token) {
      try {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
      } catch (err) {
        console.error("登出失败:", err)
      }
    }
    removeAuthToken()
    router.push("/login")
  }

  const changePassword = async (data: ChangePasswordData) => {
    setLoading(true)
    setError(null)
    const token = getAuthToken()
    if (!token) {
      setError("未登录")
      return { success: false, error: "未登录" }
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      })

      const result = await response.json()

      if (result.success) {
        return { success: true, message: result.message || "密码修改成功" }
      } else {
        setError(result.message || "密码修改失败")
        return { success: false, error: result.message || "密码修改失败" }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "密码修改失败"
      setError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      setLoading(false)
    }
  }

  return {
    login,
    logout,
    changePassword,
    loading,
    error,
    isAuthenticated: isAuthenticated(),
  }
}

