import React, { useState } from "react";
import axios from "axios";
import { useAuth } from "../hooks/useAuth";
import { Eye, EyeOff, LockKeyhole, Mail, Github, Google } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { SesameOpen } from "lucide-react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
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
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    // Implement Google OAuth logic here
    setError("Chức năng đăng nhập qua Google đang được phát triển");
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center p-4 bg-gradient-to-br from-blue-50 to-indigo-50">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 shadow-xl shadow-indigo-500/20">
            <LockKeyhole className="w-8 h-8 text-white" />
          </div>
          <h1 className="mt-4 text-3xl font-bold text-gray-900">
            Hệ thống AI Tổng Hợp
          </h1>
          <p className="text-sm text-gray-600 max-w-xl">
            Plataform quản lý văn bản hành chính với trí tuệ nhân tạo
          </p>
        </div>

        <div className="space-y-6">
          {/* Form Login */}
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-sm font-medium text-gray-700">
                Tên đăng nhập
              </Label>
              <div className="relative">
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="pr-10"
                  placeholder="Nhập tên đăng nhập hoặc email"
                />
                <Mail className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 h-5 w-5" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                Mật khẩu
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="pr-10"
                  placeholder="••••••••"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-gray-600"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <label className="flex items-center cursor-pointer">
                  <Checkbox
                    checked={rememberMe}
                    onCheckedChange={setRememberMe}
                    className="h-4 w-4 text-primary"
                  />
                  <span className="ml-2">Ghi nhớ đăng nhập</span>
                </label>
                <a href="#" className="hover:text-primary transition-colors">
                  Quên mật khẩu?
                </a>
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="h-11 w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 transition-all duration-200"
            >
              {isLoading ? (
                <>
                  <SesameOpen className="mr-2 h-4 w-4 animate-spin" />
                  Đang đăng nhập...
                </>
              ) : (
                "Đăng nhập"
              )}
            </Button>
          </form>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-destructive text-sm">
              {error}
            </div>
          )}

          {/* Divider */}
          <div className="relative text-sm text-gray-400">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase tracking-wider">
              <div className="bg-gray-50 px-3">HOẶC</div>
            </div>
          </div>

          {/* Social Login */}
          <div className="space-y-3">
            <Button
              variant="outline"
              className="h-11 w-full flex items-center justify-center gap-3 text-gray-700 hover:bg-gray-50 border-gray-300"
              onClick={handleGoogleLogin}
            >
              <Google className="h-5 w-5" />
              Đăng nhập với Google
            </Button>
            <Button
              variant="outline"
              className="h-11 w-full flex items-center justify-center gap-3 text-gray-700 hover:bg-gray-50 border-gray-300"
            >
              <Github className="h-5 w-5" />
              Đăng nhập với GitHub
            </Button>
          </div>

          {/* Footer */}
          <div className="text-center text-xs text-gray-500">
            © {new Date().getFullYear()} RAG TongHopVBHC. Bảo mật và diritti được bảo vệ.
          </div>
        </div>
      </div>
    </div>
  );
}
