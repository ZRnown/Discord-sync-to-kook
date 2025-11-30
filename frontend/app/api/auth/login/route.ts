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
    
    // 创建 AbortController 用于超时控制
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000) // 30秒超时
    
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        cache: "no-store",
        signal: controller.signal,
      })
      
      clearTimeout(timeoutId)
      
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
    } catch (fetchError: any) {
      clearTimeout(timeoutId)
      if (fetchError.name === 'AbortError') {
        console.error("登录超时: 后端服务响应时间过长")
        return NextResponse.json(
          {
            success: false,
            message: "连接超时，请检查后端服务是否正常运行",
          },
          { status: 504 }
        )
      }
      throw fetchError
    }
  } catch (error) {
    console.error("登录失败:", error)
    
    // 检查是否是连接错误
    const errorMessage = error instanceof Error ? error.message : "登录失败"
    if (errorMessage.includes("fetch failed") || errorMessage.includes("ECONNREFUSED")) {
      return NextResponse.json(
        {
          success: false,
          message: "无法连接到后端服务，请确保后端服务正在运行（端口 8000）",
        },
        { status: 503 }
      )
    }
    
    return NextResponse.json(
      {
        success: false,
        message: errorMessage,
      },
      { status: 500 }
    )
  }
}

