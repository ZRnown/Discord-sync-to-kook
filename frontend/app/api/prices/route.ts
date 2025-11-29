import { NextResponse } from "next/server"

/**
 * GET /api/prices
 * 代理到后端 API 获取实时价格
 */
export async function GET(request: Request) {
  try {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const url = `${API_BASE_URL}/api/prices`
    
    // 从请求头中获取Authorization token
    const authHeader = request.headers.get("authorization")
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }
    if (authHeader) {
      headers["Authorization"] = authHeader
    }
    
    const response = await fetch(url, {
      method: "GET",
      headers,
      cache: "no-store",
    })

    if (response.status === 401) {
      // 未授权，返回401让前端处理
      return NextResponse.json(
        {
          success: false,
          error: "未授权，请先登录",
        },
        { status: 401 }
      )
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("获取价格失败:", error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "获取价格失败",
        data: {},
      },
      { status: 500 }
    )
  }
}
