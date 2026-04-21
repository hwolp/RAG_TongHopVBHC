import { useState, useEffect } from "react";
import api from "../api";
import { Search, Plus, Lock, Unlock, Trash2, X } from "lucide-react";

export default function AdminUsers() {
  const [users, setUsers] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ username: "", full_name: "", role: "employee", department_id: 1, password: "123456" });
  const [depts, setDepts] = useState<any[]>([]);

  const fetchUsers = async () => {
    const res = await api.get(`/admin/users?search=${search}`);
    setUsers(res.data);
  };
  const fetchDepts = async () => {
    const res = await api.get("/admin/departments");
    setDepts(res.data);
  };

  useEffect(() => { fetchUsers(); fetchDepts(); }, []);

  const handleCreate = async () => {
    await api.post("/admin/users", form);
    setShowCreate(false); fetchUsers();
  };
  const handleLock = async (id: number) => {
    await api.post(`/admin/users/${id}/lock`);
    fetchUsers();
  };
  const handleDelete = async (id: number) => {
    if (confirm("Xóa tài khoản này?")) { await api.delete(`/admin/users/${id}`); fetchUsers(); }
  };

  const roleColors: any = { admin: "bg-red-100 text-red-700", manager: "bg-amber-100 text-amber-700", employee: "bg-blue-100 text-blue-700" };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quản Lý Tài Khoản</h1>
          <p className="text-gray-500 text-sm mt-1">Thêm, sửa, khóa hoặc xóa tài khoản người dùng hệ thống</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition shadow-sm">
          <Plus className="w-4 h-4" /> Thêm tài khoản
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
        <input value={search} onChange={e => { setSearch(e.target.value); }} onKeyDown={e => e.key === "Enter" && fetchUsers()}
          className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Tìm kiếm theo tên đăng nhập hoặc họ tên..." />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">ID</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Username</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Họ tên</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Vai trò</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Trạng thái</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-600">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-b hover:bg-gray-50 transition">
                <td className="px-4 py-3 text-gray-500">{u.id}</td>
                <td className="px-4 py-3 font-medium">{u.username}</td>
                <td className="px-4 py-3">{u.full_name || "—"}</td>
                <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${roleColors[u.role] || ""}`}>{u.role}</span></td>
                <td className="px-4 py-3">{u.is_locked ? <span className="text-red-600 font-medium">🔒 Bị khóa</span> : <span className="text-green-600">Hoạt động</span>}</td>
                <td className="px-4 py-3 text-right space-x-1">
                  <button onClick={() => handleLock(u.id)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500" title={u.is_locked ? "Mở khóa" : "Khóa"}>
                    {u.is_locked ? <Unlock className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                  </button>
                  <button onClick={() => handleDelete(u.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-red-500" title="Xóa"><Trash2 className="w-4 h-4" /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <p className="text-center py-8 text-gray-400">Không có dữ liệu</p>}
      </div>

      {/* Modal Tạo User */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl space-y-4">
            <div className="flex justify-between items-center"><h3 className="font-bold text-lg">Thêm tài khoản mới</h3><button onClick={() => setShowCreate(false)}><X className="w-5 h-5" /></button></div>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Tên đăng nhập" value={form.username} onChange={e => setForm({...form, username: e.target.value})} />
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Họ và tên" value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} />
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
              <option value="employee">Nhân viên</option><option value="manager">Trưởng phòng</option><option value="admin">Admin</option>
            </select>
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.department_id} onChange={e => setForm({...form, department_id: Number(e.target.value)})}>
              {depts.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Mật khẩu (mặc định: 123456)" value={form.password} onChange={e => setForm({...form, password: e.target.value})} />
            <button onClick={handleCreate} className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">Tạo tài khoản</button>
          </div>
        </div>
      )}
    </div>
  );
}
