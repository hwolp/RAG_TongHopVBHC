import React, { useState } from "react";
import axios from "axios";
import { useAuth } from "../hooks/useAuth";

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
    <div className="flex h-screen w-full items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg border border-gray-100 p-8">
        <div className="text-center mb-8">
          <div className="mx-auto bg-blue-600 h-12 w-12 rounded-lg flex items-center justify-center mb-4 shadow-blue-200 shadow-xl">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Cổng Quản Trị Hành Chính</h1>
          <p className="text-sm text-gray-500 mt-2">Vui lòng đăng nhập để sử dụng trí tuệ nhân tạo</p>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-4 text-red-700 rounded-md">
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Tên Đăng Nhập</label>
            <input 
              type="text" 
              value={username} onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all text-sm outline-none bg-gray-50 focus:bg-white"
              placeholder="VD: admin, tp_nhansu"
              required 
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Mật khẩu</label>
            <input 
              type="password" 
              value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all text-sm outline-none bg-gray-50 focus:bg-white"
              placeholder="••••••••"
              required 
            />
          </div>
          
          <button type="submit" className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-md transition-colors flex items-center justify-center space-x-2">
            Đăng Nhập Trực Tuyến
          </button>
        </form>
      </div>
    </div>
  );
}
