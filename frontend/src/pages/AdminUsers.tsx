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
    if (!window.confirm(`Xóa tài khoản "${user.username}"?`)) return;
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
    if (!window.confirm(`Xóa phòng ban "${department.name}"?`)) return;
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
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quản lý tài khoản</h1>
          <p className="text-sm text-gray-500 mt-1">Tài khoản, vai trò và phòng ban trong hệ thống.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void refreshAll()}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border bg-white text-sm text-gray-700 hover:border-blue-300"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Làm mới
          </button>
          <button
            onClick={openCreateUser}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Thêm tài khoản
          </button>
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
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Tài khoản</p>
            <Users className="w-4 h-4 text-blue-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">{stats.total}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Hoạt động</p>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-emerald-600">{stats.active}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Bị khóa</p>
            <Lock className="w-4 h-4 text-red-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-red-600">{stats.locked}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Phòng ban</p>
            <Building2 className="w-4 h-4 text-amber-500" />
          </div>
          <p className="mt-2 text-2xl font-bold text-amber-600">{stats.departments}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6 items-start">
        <section className="rounded-lg border bg-white overflow-hidden">
          <div className="p-4 border-b space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold text-gray-900">Danh sách tài khoản</h2>
                <p className="text-sm text-gray-500 mt-1">{filteredUsers.length} tài khoản đang hiển thị</p>
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
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && void runSearch()}
                  className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="Tìm username hoặc họ tên..."
                />
              </div>
              <button
                onClick={() => void runSearch()}
                className="px-4 py-2.5 rounded-lg bg-gray-100 text-gray-700 text-sm hover:bg-gray-200"
              >
                Tìm
              </button>
            </div>
          </div>

          <div className="divide-y">
            <div className="hidden lg:grid grid-cols-[minmax(220px,1.4fr)_140px_150px_120px_120px] gap-3 bg-gray-50 px-4 py-3 text-sm font-semibold text-gray-600">
              <span>Người dùng</span>
              <span>Vai trò</span>
              <span>Phòng ban</span>
              <span>Trạng thái</span>
              <span className="text-right">Hành động</span>
            </div>

            {filteredUsers.map((user) => (
              <div
                key={user.id}
                className="grid grid-cols-1 lg:grid-cols-[minmax(220px,1.4fr)_140px_150px_120px_120px] gap-3 px-4 py-4 hover:bg-gray-50"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-semibold flex-shrink-0">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 truncate">{user.full_name || user.username}</p>
                    <p className="text-xs text-gray-500 truncate">@{user.username} · ID {user.id}</p>
                  </div>
                </div>

                <div className="flex items-center">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs font-medium ${roleStyles[user.role]}`}>
                    <ShieldCheck className="w-3.5 h-3.5" />
                    {roleLabels[user.role]}
                  </span>
                </div>

                <div className="flex items-center text-sm text-gray-600">
                  <Building2 className="w-4 h-4 mr-1.5 text-gray-400 lg:hidden" />
                  <span className="truncate">
                    {user.department_id ? departmentNameMap.get(user.department_id) || `#${user.department_id}` : "Chưa gán"}
                  </span>
                </div>

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

                <div className="flex lg:justify-end gap-1">
                  <button
                    onClick={() => openEditUser(user)}
                    className="p-2 rounded-lg text-gray-500 hover:text-blue-600 hover:bg-blue-50"
                    title="Sửa tài khoản"
                  >
                    <PencilLine className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => void toggleLock(user)}
                    className="p-2 rounded-lg text-gray-500 hover:text-amber-600 hover:bg-amber-50"
                    title={user.is_locked ? "Mở khóa" : "Khóa"}
                  >
                    {user.is_locked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => void deleteUser(user)}
                    className="p-2 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50"
                    title="Xóa"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {filteredUsers.length === 0 && (
            <div className="py-14 text-center text-gray-400">
              <UserRound className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p>Không có tài khoản phù hợp.</p>
            </div>
          )}
        </section>

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

      {showUserModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-lg shadow-2xl">
            <div className="flex items-start justify-between gap-3 p-5 border-b">
              <div>
                <h3 className="font-bold text-lg text-gray-900">{editingUser ? "Chỉnh sửa tài khoản" : "Thêm tài khoản"}</h3>
                <p className="text-sm text-gray-500 mt-1">{editingUser ? `@${editingUser.username}` : "Tạo tài khoản đăng nhập mới."}</p>
              </div>
              <button onClick={() => setShowUserModal(false)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="space-y-1.5">
                  <span className="text-xs font-medium text-gray-500">Tên đăng nhập</span>
                  <input
                    value={form.username}
                    disabled={Boolean(editingUser)}
                    onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                    className="w-full border rounded-lg px-3 py-2.5 text-sm disabled:bg-gray-100"
                  />
                </label>
                <label className="space-y-1.5">
                  <span className="text-xs font-medium text-gray-500">Họ tên</span>
                  <input
                    value={form.full_name}
                    onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
                    className="w-full border rounded-lg px-3 py-2.5 text-sm"
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

              {!editingUser && (
                <label className="space-y-1.5 block">
                  <span className="text-xs font-medium text-gray-500">Mật khẩu ban đầu</span>
                  <input
                    value={form.password}
                    onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                    className="w-full border rounded-lg px-3 py-2.5 text-sm"
                    type="text"
                  />
                </label>
              )}
            </div>

            <div className="p-5 border-t flex justify-end gap-2">
              <button onClick={() => setShowUserModal(false)} className="px-4 py-2.5 rounded-lg border text-sm text-gray-600 hover:bg-gray-50">
                Hủy
              </button>
              <button
                onClick={() => void saveUser()}
                disabled={savingUser}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-60"
              >
                {editingUser ? <PencilLine className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                {savingUser ? "Đang lưu..." : editingUser ? "Lưu thay đổi" : "Tạo tài khoản"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
