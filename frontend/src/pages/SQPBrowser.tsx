import { useState, useEffect } from "react";
import api from "../api";
import { BookOpen, Search, Download, FileText } from "lucide-react";

export default function SQPBrowser() {
  const [docs, setDocs] = useState<any[]>([]);
  const [search, setSearch] = useState("");

  const fetchDocs = async () => { 
    try {
      const r = await api.get(`/employee/sqp?search=${search}`); 
      setDocs(r.data); 
    } catch {}
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleDownload = (id: number) => { 
    window.open(`http://localhost:8000/employee/documents/${id}/download`, "_blank"); 
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Quy Định & Biểu Mẫu Công Ty (SQP)</h1>
          <p className="text-gray-500 text-sm mt-1">Tra cứu các tài liệu dùng chung đã được phê duyệt</p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
        <input 
          value={search} 
          onChange={e => setSearch(e.target.value)} 
          onKeyDown={e => e.key === "Enter" && fetchDocs()}
          className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" 
          placeholder="Tìm kiếm quy định, chính sách, biểu mẫu..." 
        />
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Tên tài liệu</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-600">Ngày ban hành (Upload)</th>
              <th className="px-4 py-3 text-right font-semibold text-gray-600">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d: any) => (
              <tr key={d.id} className="border-b hover:bg-gray-50 transition">
                <td className="px-4 py-4 font-medium flex items-center gap-3">
                  <div className="p-2 bg-amber-50 rounded-lg"><BookOpen className="w-5 h-5 text-amber-600" /></div>
                  <span className="text-gray-900">{d.filename}</span>
                </td>
                <td className="px-4 py-4 text-gray-500">{d.uploaded_at?.slice(0, 10)}</td>
                <td className="px-4 py-4 text-right">
                  <button onClick={() => handleDownload(d.id)} className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg text-xs hover:bg-blue-100 ml-auto font-medium">
                    <Download className="w-3.5 h-3.5" /> Tải về
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {docs.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>Không tìm thấy quy định nào.</p>
          </div>
        )}
      </div>
    </div>
  );
}
