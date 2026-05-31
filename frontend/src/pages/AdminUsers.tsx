import { useEffect, useMemo, useState } from "react";
import api from "../api";
import {
  Building2,
  CheckCircle2,
  Lock,
  PencilLine,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Unlock,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useConfirmDialog } from "../components/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Role = "admin" | "manager" | "employee";

type UserRecord = {
  id: number;
  username: string;
  full_name?: string | null;
  role: Role;
  is_locked: boolean;
  department_id?: number | null;
};

type Department = {
  id: number;
  name: string;
};

type UserForm = {
  username: string;
  full_name: string;
  role: Role;
  department_id: string;
  password: string;
};

const emptyForm: UserForm = {
  username: "",
  full_name: "",
  role: "employee",
  department_id: "",
  password: "123456",
};

const roleLabels: Record<Role, string> = {
  admin: "Admin",
  manager: "Trưởng phòng",
  employee: "Nhân viên",
};

const roleStyles: Record<Role, string> = {
  admin: "bg-red-50 text-red-700 border-red-200",
  manager: "bg-amber-50 text-amber-700 border-amber-200",
  employee: "bg-blue-50 text-blue-700 border-blue-200",
};

function getApiError(error: unknown, fallback: string) {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    return response?.data?.detail || fallback;
  }
  return fallback;
}

export default function AdminUsers() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "all">("all");
  const [loading, setLoading] = useState(false);
  const [savingUser, setSavingUser] = useState(false);
  const [savingDepartment, setSavingDepartment] = useState(false);
  const [error, setError] = useState("");
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [form, setForm] = useState<UserForm>(emptyForm);
  const [departmentName, setDepartmentName] = useState("");
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null);
  const { confirm, confirmDialog } = useConfirmDialog();

  const departmentNameMap = useMemo(
    () => new Map(departments.map((department) => [department.id, department.name])),
    [departments],
  );

  const departmentUserCount = useMemo(() => {
    const count = new Map<number, number>();
    users.forEach((user) => {
      if (user.department_id !== null && user.department_id !== undefined) {
        count.set(user.department_id, (count.get(user.department_id) || 0) + 1);
      }
    });
    return count;
  }, [users]);

  const filteredUsers = useMemo(
    () => users.filter((user) => roleFilter === "all" || user.role === roleFilter),
    [roleFilter, users],
  );

  const stats = useMemo(() => ({
    total: users.length,
    active: users.filter((user) => !user.is_locked).length,
    locked: users.filter((user) => user.is_locked).length,
    departments: departments.filter((department) => department.id !== 0).length,
  }), [departments, users]);

  const fetchUsers = async () => {
    const response = await api.get(`/admin/users?search=${encodeURIComponent(search)}`);
    setUsers(response.data);
  };

  const fetchDepartments = async () => {
    const response = await api.get("/admin/departments");
    setDepartments(response.data);
    if (!form.department_id && response.data.length > 0) {
      const firstNormalDepartment = response.data.find((department: Department) => department.id !== 0) || response.data[0];
      setForm((current) => ({ ...current, department_id: String(firstNormalDepartment.id) }));
    }
  };

  const refreshAll = async () => {
    setLoading(true);
    setError("");
    try {
      await Promise.all([fetchUsers(), fetchDepartments()]);
    } catch (err) {
      setError(getApiError(err, "Không thể tải dữ liệu quản trị."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreateUser = () => {
    setEditingUser(null);
    setForm({
      ...emptyForm,
      department_id: departments.find((department) => department.id !== 0)?.id.toString() || departments[0]?.id.toString() || "",
    });
    setShowUserModal(true);
  };

  const openEditUser = (user: UserRecord) => {
    setEditingUser(user);
    setForm({
      username: user.username,
      full_name: user.full_name || "",
      role: user.role,
      department_id: user.department_id ? String(user.department_id) : "",
      password: "",
    });
    setShowUserModal(true);
  };

  const saveUser = async () => {
    if (!form.username.trim() && !editingUser) {
      setError("Tên đăng nhập không được để trống.");
      return;
    }
    setSavingUser(true);
    setError("");
    try {
      const payload = {
        username: form.username.trim(),
        full_name: form.full_name.trim(),
        role: form.role,
        department_id: form.department_id ? Number(form.department_id) : null,
        password: form.password || "123456",
      };

      if (editingUser) {
        await api.put(`/admin/users/${editingUser.id}`, {
          full_name: payload.full_name,
          role: payload.role,
          department_id: payload.department_id,
          password: form.password.trim() || undefined,
        });
      } else {
        await api.post("/admin/users", payload);
      }

      setShowUserModal(false);
      await fetchUsers();
    } catch (err) {
      setError(getApiError(err, "Không thể lưu tài khoản."));
    } finally {
      setSavingUser(false);
    }
  };

  const toggleLock = async (user: UserRecord) => {
    setError("");
    try {
      await api.post(`/admin/users/${user.id}/lock`);
      await fetchUsers();
    } catch (err) {
      setError(getApiError(err, "Không thể cập nhật trạng thái tài khoản."));
    }
  };

  const deleteUser = async (user: UserRecord) => {
    const ok = await confirm({
      title: `Xóa tài khoản "${user.username}"?`,
      description: "Tài khoản sẽ bị xóa khỏi hệ thống.",
      confirmText: "Xóa tài khoản",
    });
    if (!ok) return;
    setError("");
    try {
      await api.delete(`/admin/users/${user.id}`);
      await fetchUsers();
    } catch (err) {
      setError(getApiError(err, "Không thể xóa tài khoản."));
    }
  };

  const saveDepartment = async () => {
    const name = departmentName.trim();
    if (!name) {
      setError("Tên phòng ban không được để trống.");
      return;
    }

    setSavingDepartment(true);
    setError("");
    try {
      if (editingDepartment) {
        await api.put(`/admin/departments/${editingDepartment.id}`, { name });
      } else {
        await api.post("/admin/departments", { name });
      }
      setDepartmentName("");
      setEditingDepartment(null);
      await fetchDepartments();
    } catch (err) {
      setError(getApiError(err, "Không thể lưu phòng ban."));
    } finally {
      setSavingDepartment(false);
    }
  };

  const startEditDepartment = (department: Department) => {
    setEditingDepartment(department);
    setDepartmentName(department.name);
  };

  const cancelEditDepartment = () => {
    setEditingDepartment(null);
    setDepartmentName("");
  };

  const deleteDepartment = async (department: Department) => {
    const ok = await confirm({
      title: `Xóa phòng ban "${department.name}"?`,
      description: "Phòng ban sẽ bị xóa khỏi hệ thống nếu backend cho phép.",
      confirmText: "Xóa phòng ban",
    });
    if (!ok) return;
    setError("");
    try {
      await api.delete(`/admin/departments/${department.id}`);
      await fetchDepartments();
    } catch (err) {
      setError(getApiError(err, "Không thể xóa phòng ban."));
    }
  };

  const runSearch = async () => {
    setLoading(true);
    setError("");
    try {
      await fetchUsers();
    } catch (err) {
      setError(getApiError(err, "Không thể tìm kiếm tài khoản."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-page">
      {confirmDialog}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Quản lý tài khoản</h1>
          <p className="text-sm text-muted-foreground mt-1">Tài khoản, vai trò và phòng ban trong hệ thống.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => void refreshAll()}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Làm mới
          </Button>
          <Button
            type="button"
            onClick={openCreateUser}
          >
            <Plus className="w-4 h-4" />
            Thêm tài khoản
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <span>{error}</span>
          <button onClick={() => setError("")} className="text-red-500 hover:text-red-700">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <Card className="glass-panel p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Tài khoản</p>
            <Users className="w-4 h-4 text-blue-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">{stats.total}</p>
        </Card>
        <Card className="glass-panel p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Hoạt động</p>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-600">{stats.active}</p>
        </Card>
        <Card className="glass-panel p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Bị khóa</p>
            <Lock className="w-4 h-4 text-red-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-red-600">{stats.locked}</p>
        </Card>
        <Card className="glass-panel p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Phòng ban</p>
            <Building2 className="w-4 h-4 text-amber-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-600">{stats.departments}</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6 items-start">
        <Card className="glass-panel overflow-hidden">
          <div className="p-4 border-b space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold">Danh sách tài khoản</h2>
                <p className="text-sm text-muted-foreground mt-1">{filteredUsers.length} tài khoản đang hiển thị</p>
              </div>
              <div className="flex rounded-lg border overflow-hidden text-sm">
                {[
                  { key: "all", label: "Tất cả" },
                  { key: "admin", label: "Admin" },
                  { key: "manager", label: "Trưởng phòng" },
                  { key: "employee", label: "Nhân viên" },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setRoleFilter(item.key as Role | "all")}
                    className={`px-3 py-2 ${roleFilter === item.key ? "bg-slate-900 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                <Input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && void runSearch()}
                  className="pl-10"
                  placeholder="Tìm username hoặc họ tên..."
                />
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => void runSearch()}
              >
                Tìm
              </Button>
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Người dùng</TableHead>
                <TableHead>Vai trò</TableHead>
                <TableHead>Phòng ban</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead className="text-right">Hành động</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
            {filteredUsers.map((user) => (
              <TableRow key={user.id}>
                <TableCell>
                <div className="flex min-w-0 items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-semibold flex-shrink-0">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 truncate">{user.full_name || user.username}</p>
                    <p className="text-xs text-gray-500 truncate">@{user.username} · ID {user.id}</p>
                  </div>
                </div>
                </TableCell>

                <TableCell>
                  <Badge variant="outline" className={roleStyles[user.role]}>
                    <ShieldCheck className="w-3.5 h-3.5" />
                    {roleLabels[user.role]}
                  </Badge>
                </TableCell>

                <TableCell className="text-muted-foreground">
                <div className="flex items-center text-sm">
                  <Building2 className="w-4 h-4 mr-1.5 text-gray-400 lg:hidden" />
                  <span className="truncate">
                    {user.department_id ? departmentNameMap.get(user.department_id) || `#${user.department_id}` : "Chưa gán"}
                  </span>
                </div>
                </TableCell>

                <TableCell>
                <div className="flex items-center text-sm">
                  {user.is_locked ? (
                    <span className="inline-flex items-center gap-1.5 text-red-600 font-medium">
                      <Lock className="w-4 h-4" />
                      Bị khóa
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-emerald-600 font-medium">
                      <CheckCircle2 className="w-4 h-4" />
                      Hoạt động
                    </span>
                  )}
                </div>
                </TableCell>

                <TableCell>
                <div className="flex justify-end gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => openEditUser(user)}
                    title="Sửa tài khoản"
                  >
                    <PencilLine className="w-4 h-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => void toggleLock(user)}
                    title={user.is_locked ? "Mở khóa" : "Khóa"}
                  >
                    {user.is_locked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => void deleteUser(user)}
                    className="text-destructive"
                    title="Xóa"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                </TableCell>
              </TableRow>
            ))}
            </TableBody>
          </Table>

          {filteredUsers.length === 0 && (
            <div className="py-14 text-center text-gray-400">
              <UserRound className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p>Không có tài khoản phù hợp.</p>
            </div>
          )}
        </Card>

        <aside className="rounded-lg border bg-white overflow-hidden">
          <div className="p-4 border-b flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-gray-900">Phòng ban</h2>
              <p className="text-sm text-gray-500 mt-1">Quản lý đơn vị và số tài khoản được gán.</p>
            </div>
            {editingDepartment && (
              <button onClick={cancelEditDepartment} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="p-4 border-b space-y-2">
            <input
              value={departmentName}
              onChange={(event) => setDepartmentName(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && void saveDepartment()}
              className="w-full border rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Tên phòng ban"
            />
            <button
              onClick={() => void saveDepartment()}
              disabled={savingDepartment || !departmentName.trim()}
              className="w-full inline-flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-slate-900 text-white text-sm hover:bg-slate-800 disabled:opacity-60"
            >
              {editingDepartment ? <PencilLine className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
              {savingDepartment ? "Đang lưu..." : editingDepartment ? "Lưu phòng ban" : "Thêm phòng ban"}
            </button>
          </div>

          <div className="divide-y">
            {departments.map((department) => {
              const userCount = departmentUserCount.get(department.id) || 0;
              const isSystemDepartment = department.id === 0;
              return (
                <div key={department.id} className="p-4 flex items-center justify-between gap-3 hover:bg-gray-50">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-amber-500 flex-shrink-0" />
                      <p className="font-medium text-gray-900 truncate">{department.name}</p>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{userCount} tài khoản · ID {department.id}</p>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => startEditDepartment(department)}
                      disabled={isSystemDepartment}
                      className="p-2 rounded-lg text-gray-500 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-40"
                      title="Sửa phòng ban"
                    >
                      <PencilLine className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => void deleteDepartment(department)}
                      disabled={isSystemDepartment}
                      className="p-2 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 disabled:opacity-40"
                      title="Xóa phòng ban"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {departments.length === 0 && (
            <div className="py-10 text-center text-gray-400">
              <Building2 className="w-9 h-9 mx-auto mb-2 opacity-40" />
              <p>Chưa có phòng ban.</p>
            </div>
          )}
        </aside>
      </div>

      <Dialog open={showUserModal} onOpenChange={setShowUserModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingUser ? "Chỉnh sửa tài khoản" : "Thêm tài khoản"}</DialogTitle>
            <DialogDescription>{editingUser ? `@${editingUser.username}` : "Tạo tài khoản đăng nhập mới."}</DialogDescription>
          </DialogHeader>

            <div className="p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="space-y-1.5">
                  <span className="text-xs font-medium text-gray-500">Tên đăng nhập</span>
                  <Input
                    value={form.username}
                    disabled={Boolean(editingUser)}
                    onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                  />
                </label>
                <label className="space-y-1.5">
                  <span className="text-xs font-medium text-gray-500">Họ tên</span>
                  <Input
                    value={form.full_name}
                    onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
                  />
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="space-y-1.5">
                  <span className="text-xs font-medium text-gray-500">Vai trò</span>
                  <select
                    value={form.role}
                    onChange={(event) => setForm((current) => ({ ...current, role: event.target.value as Role }))}
                    className="w-full border rounded-lg px-3 py-2.5 text-sm"
                  >
                    <option value="employee">Nhân viên</option>
                    <option value="manager">Trưởng phòng</option>
                    <option value="admin">Admin</option>
                  </select>
                </label>
                <label className="space-y-1.5">
                  <span className="text-xs font-medium text-gray-500">Phòng ban</span>
                  <select
                    value={form.department_id}
                    onChange={(event) => setForm((current) => ({ ...current, department_id: event.target.value }))}
                    className="w-full border rounded-lg px-3 py-2.5 text-sm"
                  >
                    <option value="">Chưa gán</option>
                    {departments.map((department) => (
                      <option key={department.id} value={department.id}>
                        {department.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {editingUser ? (
                <label className="space-y-1.5 block">
                  <span className="text-xs font-medium text-gray-500">Mật khẩu mới</span>
                  <Input
                    value={form.password}
                    onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                    type="password"
                    placeholder="Để trống nếu không đổi"
                    autoComplete="new-password"
                  />
                </label>
              ) : (
                <label className="space-y-1.5 block">
                  <span className="text-xs font-medium text-gray-500">Mật khẩu ban đầu</span>
                  <Input
                    value={form.password}
                    onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                    type="text"
                  />
                </label>
              )}
            </div>

            <div className="flex justify-end gap-2 border-t p-5">
              <Button type="button" variant="outline" onClick={() => setShowUserModal(false)}>
                Hủy
              </Button>
              <Button
                type="button"
                onClick={() => void saveUser()}
                disabled={savingUser}
              >
                {editingUser ? <PencilLine className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                {savingUser ? "Đang lưu..." : editingUser ? "Lưu thay đổi" : "Tạo tài khoản"}
              </Button>
            </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
