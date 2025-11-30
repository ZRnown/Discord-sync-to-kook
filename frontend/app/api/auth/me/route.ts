import { NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  try {
    const token = request.headers.get("authorization")
    if (!token) {
      return NextResponse.json({ error: "未授权" }, { status: 401 })
    }

    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: {
        Authorization: token,
      },
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error("获取用户信息失败:", error)
    return NextResponse.json(
      { error: "获取用户信息失败" },
      { status: 500 }
    )
  }
}

