import { useState, useEffect } from "react";
import { jwtDecode } from "jwt-decode";

export interface UserTokenPayload {
  sub: string;
  role: string;
  id: number;
  exp: number;
}

export function useAuth() {
  const [user, setUser] = useState<UserTokenPayload | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mỗi khi Load trang sẽ kiểm tra kho lưu JWT
    const token = localStorage.getItem("token");
    if (token) {
      try {
        const decoded: UserTokenPayload = jwtDecode(token);
        // Kiểm tra xem hạn token còn không
        if (decoded.exp * 1000 > Date.now()) {
          setUser(decoded);
        } else {
          localStorage.removeItem("token");
        }
      } catch (e) {
        console.error("Token Invalid", e);
        localStorage.removeItem("token");
      }
    }
    setLoading(false);
  }, []);

  const login = (token: string) => {
    localStorage.setItem("token", token);
    const decoded: UserTokenPayload = jwtDecode(token);
    setUser(decoded);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return { user, loading, login, logout };
}
