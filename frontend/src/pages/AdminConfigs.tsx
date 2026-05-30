import { useEffect, useState } from "react";
import { RotateCcw, Save, ServerCog } from "lucide-react";
import api from "../api";

type SystemConfig = {
  id: number;
  key: string;
  value: string;
  type: string;
  label?: string;
  description?: string;
  input_type?: "text" | "number";
};

export default function AdminConfigs() {
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [configValues, setConfigValues] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState("");
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState("");

  const fetchConfigs = async () => {
    const response = await api.get<SystemConfig[]>("/admin/configs", { params: { type: "system" } });
    setConfigs(response.data);
    setConfigValues(Object.fromEntries(response.data.map(item => [item.key, item.value])));
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  const handleSaveConfig = async (item: SystemConfig) => {
    const value = (configValues[item.key] ?? "").trim();
    if (!value) {
      setMessage("Giá trị cấu hình không được để trống.");
      return;
    }

    setSavingKey(item.key);
    setMessage("");
    try {
      await api.put(`/admin/configs/${item.id}`, { value });
      await fetchConfigs();
      setMessage(`Đã lưu ${item.label || item.key}. Cấu hình áp dụng cho request/job mới.`);
    } finally {
      setSavingKey("");
    }
  };

  const handleResetConfigs = async () => {
    const ok = confirm("Reset toàn bộ cấu hình hệ thống về giá trị mặc định ban đầu?");
    if (!ok) return;

    setResetting(true);
    setMessage("");
    try {
      await api.post("/admin/configs/system/reset");
      await fetchConfigs();
      setMessage("Đã reset cấu hình về giá trị mặc định ban đầu.");
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cấu Hình Hệ Thống</h1>
          <p className="text-sm text-gray-500 mt-1">Quản lý cấu hình Ollama, RAG và thư mục upload.</p>
        </div>
        <button
          onClick={handleResetConfigs}
          disabled={resetting}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:border-amber-300 hover:text-amber-700 disabled:opacity-60"
        >
          <RotateCcw className={`w-4 h-4 ${resetting ? "animate-spin" : ""}`} />
          Reset mặc định
        </button>
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-6">
        <div className="flex items-center gap-3 mb-5">
          <ServerCog className="w-5 h-5 text-teal-700" />
          <div>
            <h3 className="font-semibold text-gray-900">RAG / Ollama / Upload</h3>
            <p className="text-sm text-gray-500">Giá trị mặc định được lấy từ cấu hình hiện tại của backend.</p>
          </div>
        </div>

        {message && (
          <div className="mb-4 rounded-lg border border-teal-100 bg-teal-50 px-4 py-3 text-sm text-teal-700">
            {message}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {configs.map(item => (
            <div key={item.key} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <label className="block text-sm font-semibold text-gray-800 mb-1">{item.label || item.key}</label>
              <p className="text-xs text-gray-500 mb-3 min-h-8">{item.description}</p>
              <div className="flex gap-2">
                <input
                  type={item.input_type === "number" ? "number" : "text"}
                  value={configValues[item.key] ?? ""}
                  onChange={event => setConfigValues(prev => ({ ...prev, [item.key]: event.target.value }))}
                  className="min-w-0 flex-1 border rounded-lg px-3 py-2 text-sm bg-white"
                />
                <button
                  onClick={() => handleSaveConfig(item)}
                  disabled={savingKey === item.key}
                  className="shrink-0 inline-flex items-center justify-center rounded-lg bg-[#006666] px-3 py-2 text-white hover:bg-[#005252] disabled:opacity-60"
                  title="Lưu cấu hình"
                >
                  <Save className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
