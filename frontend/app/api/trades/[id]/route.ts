import { NextResponse } from "next/server"

/**
 * DELETE /api/trades/[id]
 * 删除指定的交易单
 */
export async function DELETE(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const tradeId = params.id
    const url = `${API_BASE_URL}/api/trades/${tradeId}`
    
    // 从请求头中获取Authorization token
    const authHeader = request.headers.get("authorization")
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    }
    if (authHeader) {
      headers["Authorization"] = authHeader
    }
    
    const response = await fetch(url, {
      method: "DELETE",
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
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("删除交易单失败:", error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "删除交易单失败",
      },
      { status: 500 }
    )
  }
}

