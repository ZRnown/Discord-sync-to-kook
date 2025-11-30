import { NextResponse } from "next/server"

/**
 * POST /api/auth/change-password
 * 代理到后端 API 修改密码
 */
export async function POST(request: Request) {
  try {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const url = `${API_BASE_URL}/api/auth/change-password`
    
    const body = await request.json()
    
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
      body: JSON.stringify(body),
      cache: "no-store",
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      return NextResponse.json(
        {
          success: false,
          message: data.detail || data.message || "密码修改失败",
        },
        { status: response.status }
      )
    }
    
    return NextResponse.json(data)
  } catch (error) {
    console.error("密码修改失败:", error)
    return NextResponse.json(
      {
        success: false,
        message: error instanceof Error ? error.message : "密码修改失败",
      },
      { status: 500 }
    )
  }
}

