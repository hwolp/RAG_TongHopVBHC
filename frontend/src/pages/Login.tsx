import React, { useState } from "react";
import axios from "axios";
import { useAuth } from "../hooks/useAuth";
import { LockKeyhole } from "lucide-react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Gọi lên Backend tạo sẵn ở localhost:8000
      const res = await axios.post("http://localhost:8000/auth/login", {
        username: username,
        password: password,
      });
      // Lấy được thẻ chứng minh phân quyền JWT!
      const token = res.data.access_token;
      login(token);
      window.location.href = "/"; // Quay lại trang Dashboard
    } catch (err: any) {
      setError(err.response?.data?.detail || "Đăng nhập thất bại. Vui lòng thử lại.");
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center p-6">
      <div className="neo-panel w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="mx-auto bg-[#006666] h-14 w-14 rounded-lg flex items-center justify-center mb-5 text-white shadow-[8px_8px_18px_rgba(0,62,62,0.24),-8px_-8px_18px_rgba(255,255,255,0.72)]">
            <LockKeyhole className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Cổng Quản Trị Hành Chính</h1>
          <p className="text-sm text-slate-500 mt-2">Vui lòng đăng nhập để sử dụng trí tuệ nhân tạo</p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50/70 p-4 text-red-700">
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Tên Đăng Nhập</label>
            <input 
              type="text" 
              value={username} onChange={(e) => setUsername(e.target.value)}
              className="neo-input px-4 py-3"
              placeholder="VD: admin, tp_nhansu"
              required 
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Mật khẩu</label>
            <input 
              type="password" 
              value={password} onChange={(e) => setPassword(e.target.value)}
              className="neo-input px-4 py-3"
              placeholder="••••••••"
              required 
            />
          </div>
          
          <button type="submit" className="neo-button neo-button-primary w-full py-3 px-4">
            Đăng Nhập Trực Tuyến
          </button>
        </form>
      </div>
    </div>
  );
}
