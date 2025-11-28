import { NextResponse } from "next/server"
import { getTraders } from "@/lib/api-client"

/**
 * GET /api/traders
 * 代理到后端 API 获取交易员列表
 */
export async function GET() {
  try {
    const response = await getTraders()
    return NextResponse.json(response)
  } catch (error) {
    console.error("获取交易员列表失败:", error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "获取交易员列表失败",
        data: [],
      },
      { status: 500 }
    )
  }
}
