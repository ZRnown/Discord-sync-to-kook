import { NextResponse } from "next/server"
import { getTrades } from "@/lib/api-client"

/**
 * GET /api/trades
 * 代理到后端 API 获取交易单列表
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const channelId = searchParams.get("channel_id") || undefined

    const response = await getTrades(channelId)
    return NextResponse.json(response)
  } catch (error) {
    console.error("获取交易单列表失败:", error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "获取交易单列表失败",
        data: [],
      },
      { status: 500 }
    )
  }
}
