"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Textarea } from "@/components/ui/textarea"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ArrowLeft, Plus, Edit, Trash2, Eye, EyeOff } from "lucide-react"
import { getAuthToken } from "@/lib/auth"

interface User {
  id: number
  username: string
  role: string
  note?: string
  created_at: number
  updated_at?: number
}

export default function AdminPage() {
  const router = useRouter()
  const { isAuthenticated, isAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedUsers, setSelectedUsers] = useState<Set<number>>(new Set())
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [passwordHints, setPasswordHints] = useState<Record<number, string>>({})
  const [showPasswordHints, setShowPasswordHints] = useState<Record<number, boolean>>({})
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    role: "user",
    note: "",
  })

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login")
      return
    }
    if (!isAdmin) {
      router.push("/")
      return
    }
    fetchUsers()
  }, [isAuthenticated, isAdmin, router])

  const fetchUsers = async () => {
    try {
      const token = getAuthToken()
      const response = await fetch("/api/users", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      const data = await response.json()
      if (data.success) {
        setUsers(data.data)
      }
    } catch (error) {
      console.error("获取用户列表失败:", error)
    } finally {
      setLoading(false)
    }
  }

  const fetchPasswordHint = async (userId: number) => {
    try {
      const token = getAuthToken()
      const response = await fetch(`/api/users/${userId}/password-info`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data.password_hint) {
        setPasswordHints((prev) => ({
          ...prev,
          [userId]: data.data.password_hint,
        }))
        setShowPasswordHints((prev) => ({
          ...prev,
          [userId]: true,
        }))
      }
    } catch (error) {
      console.error("获取密码提示失败:", error)
    }
  }

  const handleCreate = async () => {
    try {
      const token = getAuthToken()
      const response = await fetch("/api/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      })

      const data = await response.json()
      if (response.ok && data.id) {
        setShowCreateDialog(false)
        setFormData({ username: "", password: "", role: "user", note: "" })
        fetchUsers()
      } else {
        alert(data.detail || "创建用户失败")
      }
    } catch (error) {
      console.error("创建用户失败:", error)
      alert("创建用户失败")
    }
  }

  const handleEdit = async (user: User) => {
    setEditingUser(user)
    setFormData({
      username: user.username,
      password: "",
      role: user.role,
      note: user.note || "",
    })
    // 获取密码提示
    await fetchPasswordHint(user.id)
    setShowEditDialog(true)
  }

  const handleUpdate = async () => {
    if (!editingUser) return

    try {
      const token = getAuthToken()
      const updateData: any = {}
      if (formData.username !== editingUser.username) {
        updateData.username = formData.username
      }
      if (formData.password) {
        updateData.password = formData.password
      }
      if (formData.role !== editingUser.role) {
        updateData.role = formData.role
      }
      if (formData.note !== (editingUser.note || "")) {
        updateData.note = formData.note
      }

      if (Object.keys(updateData).length === 0) {
        setShowEditDialog(false)
        return
      }

      const response = await fetch(`/api/users/${editingUser.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updateData),
      })

      const data = await response.json()
      if (response.ok && data.id) {
        setShowEditDialog(false)
        setEditingUser(null)
        setFormData({ username: "", password: "", role: "user", note: "" })
        setShowPasswordHints({})
        setPasswordHints({})
        fetchUsers()
      } else {
        alert(data.detail || "更新用户失败")
      }
    } catch (error) {
      console.error("更新用户失败:", error)
      alert("更新用户失败")
    }
  }

  const handleDelete = async (userId: number) => {
    if (!confirm("确定要删除这个用户吗？此操作无法撤销。")) {
      return
    }

    try {
      const token = getAuthToken()
      const response = await fetch(`/api/users/${userId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      const data = await response.json()
      if (data.success) {
        fetchUsers()
        setSelectedUsers((prev) => {
          const newSet = new Set(prev)
          newSet.delete(userId)
          return newSet
        })
      } else {
        alert(data.detail || "删除用户失败")
      }
    } catch (error) {
      console.error("删除用户失败:", error)
      alert("删除用户失败")
    }
  }

  const handleBatchDelete = async () => {
    if (selectedUsers.size === 0) {
      alert("请先选择要删除的用户")
      return
    }

    if (!confirm(`确定要删除选中的 ${selectedUsers.size} 个用户吗？此操作无法撤销。`)) {
      return
    }

    try {
      const token = getAuthToken()
      const response = await fetch("/api/users/batch-delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_ids: Array.from(selectedUsers) }),
      })

      const data = await response.json()
      if (data.success) {
        fetchUsers()
        setSelectedUsers(new Set())
      } else {
        alert(data.detail || "批量删除失败")
      }
    } catch (error) {
      console.error("批量删除失败:", error)
      alert("批量删除失败")
    }
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedUsers(new Set(users.map((u) => u.id)))
    } else {
      setSelectedUsers(new Set())
    }
  }

  const handleSelectUser = (userId: number, checked: boolean) => {
    setSelectedUsers((prev) => {
      const newSet = new Set(prev)
      if (checked) {
        newSet.add(userId)
      } else {
        newSet.delete(userId)
      }
      return newSet
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    )
  }

  const allSelected = users.length > 0 && selectedUsers.size === users.length
  const someSelected = selectedUsers.size > 0 && selectedUsers.size < users.length

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" onClick={() => router.push("/")}>
                <ArrowLeft className="w-5 h-5" />
              </Button>
              <h1 className="text-lg font-semibold">用户管理</h1>
            </div>
            <div className="flex items-center gap-2">
              {selectedUsers.size > 0 && (
                <Button
                  variant="destructive"
                  onClick={handleBatchDelete}
                  className="gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  批量删除 ({selectedUsers.size})
                </Button>
              )}
              <Button onClick={() => setShowCreateDialog(true)} className="gap-2">
                <Plus className="w-4 h-4" />
                创建用户
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <Card>
          <CardHeader>
            <CardTitle>用户列表</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={allSelected}
                      onCheckedChange={handleSelectAll}
                      aria-label="全选"
                    />
                  </TableHead>
                  <TableHead>ID</TableHead>
                  <TableHead>用户名</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>备注</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      暂无用户
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedUsers.has(user.id)}
                          onCheckedChange={(checked) =>
                            handleSelectUser(user.id, checked as boolean)
                          }
                          aria-label={`选择 ${user.username}`}
                        />
                      </TableCell>
                      <TableCell>{user.id}</TableCell>
                      <TableCell className="font-medium">{user.username}</TableCell>
                      <TableCell>
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            user.role === "admin"
                              ? "bg-primary/20 text-primary"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {user.role === "admin" ? "管理员" : "普通用户"}
                        </span>
                      </TableCell>
                      <TableCell className="max-w-xs truncate" title={user.note || ""}>
                        {user.note || "—"}
                      </TableCell>
                      <TableCell>
                        {user.created_at
                          ? new Date(user.created_at * 1000).toLocaleString("zh-CN")
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleEdit(user)}
                            className="h-8 w-8"
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(user.id)}
                            className="h-8 w-8 text-destructive hover:text-destructive"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </main>

      {/* 创建用户对话框 */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>创建用户</DialogTitle>
            <DialogDescription>创建一个新用户账户</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="create-username">用户名</Label>
              <Input
                id="create-username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="请输入用户名"
              />
            </div>
            <div>
              <Label htmlFor="create-password">密码</Label>
              <Input
                id="create-password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="请输入密码"
              />
            </div>
            <div>
              <Label htmlFor="create-role">角色</Label>
              <Select
                value={formData.role}
                onValueChange={(value) => setFormData({ ...formData, role: value })}
              >
                <SelectTrigger id="create-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">普通用户</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="create-note">备注</Label>
              <Textarea
                id="create-note"
                value={formData.note}
                onChange={(e) => setFormData({ ...formData, note: e.target.value })}
                placeholder="请输入备注（可选）"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              取消
            </Button>
            <Button onClick={handleCreate}>创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑用户对话框 */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>编辑用户</DialogTitle>
            <DialogDescription>修改用户信息</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-username">用户名</Label>
              <Input
                id="edit-username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="请输入用户名"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label htmlFor="edit-password">新密码（留空则不修改）</Label>
                {editingUser && passwordHints[editingUser.id] && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (!showPasswordHints[editingUser.id]) {
                        fetchPasswordHint(editingUser.id)
                      } else {
                        setShowPasswordHints((prev) => ({
                          ...prev,
                          [editingUser.id]: false,
                        }))
                      }
                    }}
                    className="h-7 text-xs gap-1"
                  >
                    {showPasswordHints[editingUser.id] ? (
                      <>
                        <EyeOff className="w-3 h-3" />
                        隐藏
                      </>
                    ) : (
                      <>
                        <Eye className="w-3 h-3" />
                        查看密码提示
                      </>
                    )}
                  </Button>
                )}
              </div>
              <Input
                id="edit-password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="留空则不修改密码"
              />
              {editingUser &&
                showPasswordHints[editingUser.id] &&
                passwordHints[editingUser.id] && (
                  <p className="text-xs text-muted-foreground mt-1">
                    当前密码哈希: {passwordHints[editingUser.id]}
                  </p>
                )}
            </div>
            <div>
              <Label htmlFor="edit-role">角色</Label>
              <Select
                value={formData.role}
                onValueChange={(value) => setFormData({ ...formData, role: value })}
              >
                <SelectTrigger id="edit-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">普通用户</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="edit-note">备注</Label>
              <Textarea
                id="edit-note"
                value={formData.note}
                onChange={(e) => setFormData({ ...formData, note: e.target.value })}
                placeholder="请输入备注（可选）"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              取消
            </Button>
            <Button onClick={handleUpdate}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
