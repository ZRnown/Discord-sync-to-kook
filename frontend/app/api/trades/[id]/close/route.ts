import { NextResponse } from "next/server"

/**
 * POST /api/trades/[id]/close
 * 手动结单
 */
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const params = await context.params
    const tradeId = params.id
    const url = `${API_BASE_URL}/api/trades/${tradeId}/close`
    
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

    if (response.status === 401) {
      return NextResponse.json(
        {
          success: false,
          error: "未授权，请先登录",
        },
        { status: 401 }
      )
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || errorData.error || errorData.message || `HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("手动结单失败:", error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "手动结单失败",
      },
      { status: 500 }
    )
  }
}

