import { NextResponse } from "next/server"

/**
 * POST /api/auth/logout
 * 代理到后端 API 登出
 */
export async function POST(request: Request) {
  try {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const url = `${API_BASE_URL}/api/auth/logout`
    
    // 从请求头中获取Authorization token
    const authHeader = request.headers.get("authorization")
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }
    if (authHeader) {
      headers["Authorization"] = authHeader
    }
    
    const response = await fetch(url, {
      method: "POST",
      headers,
      cache: "no-store",
    })
    
    const data = await response.json().catch(() => ({ success: true }))
    
    return NextResponse.json(data)
  } catch (error) {
    console.error("登出失败:", error)
    // 即使后端登出失败，前端也清除 token
    return NextResponse.json({ success: true })
  }
}

