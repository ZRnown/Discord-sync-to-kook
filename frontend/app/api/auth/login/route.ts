import { NextResponse } from "next/server"

/**
 * POST /api/auth/login
 * 代理到后端 API 登录
 */
export async function POST(request: Request) {
  try {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const url = `${API_BASE_URL}/api/auth/login`
    
    const body = await request.json()
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      return NextResponse.json(
        {
          success: false,
          message: data.detail || data.message || "登录失败",
        },
        { status: response.status }
      )
    }
    
    return NextResponse.json(data)
  } catch (error) {
    console.error("登录失败:", error)
    return NextResponse.json(
      {
        success: false,
        message: error instanceof Error ? error.message : "登录失败",
      },
      { status: 500 }
    )
  }
}

