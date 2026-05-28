import axios from "axios";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: apiBaseUrl,
});

export type JobStatus = "queued" | "running" | "success" | "failed";

export type BaseJobResponse = {
  id: number;
  status: JobStatus;
  progress?: number;
  result?: unknown;
  error?: string | null;
};

// Tự động gắn JWT token vào mọi request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Tự động xử lý lỗi 401 (hết hạn token)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export async function waitForJob<T extends BaseJobResponse = BaseJobResponse>(
  jobId: number,
  timeoutSeconds = 600,
): Promise<T> {
  const response = await api.get<T>(`/jobs/${jobId}/wait`, {
    params: { timeout_seconds: timeoutSeconds },
  });
  return response.data;
}

export default api;
