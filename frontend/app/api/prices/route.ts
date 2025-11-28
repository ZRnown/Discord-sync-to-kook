import { NextResponse } from "next/server"
import { getPrices } from "@/lib/api-client"

/**
 * GET /api/prices
 * 代理到后端 API 获取实时价格
 */
export async function GET() {
  try {
    const response = await getPrices()
    return NextResponse.json(response)
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
