import { NextRequest, NextResponse } from "next/server"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const token = request.headers.get("authorization")
    if (!token) {
      return NextResponse.json({ error: "未授权" }, { status: 401 })
    }

    const body = await request.json()
    const userId = params.id

    const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: token,
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error("更新用户失败:", error)
    return NextResponse.json(
      { error: "更新用户失败" },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const token = request.headers.get("authorization")
    if (!token) {
      return NextResponse.json({ error: "未授权" }, { status: 401 })
    }

    const userId = params.id

    const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
      method: "DELETE",
      headers: {
        Authorization: token,
      },
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error("删除用户失败:", error)
    return NextResponse.json(
      { error: "删除用户失败" },
      { status: 500 }
    )
  }
}

