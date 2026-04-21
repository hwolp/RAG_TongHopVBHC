import { useState } from 'react';
import { UploadCloud, File, X, CheckCircle } from 'lucide-react';

const Upload = () => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const simulateUpload = () => {
    if (!file) return;
    setUploading(true);
    setTimeout(() => {
      setUploading(false);
      setSuccess(true);
    }, 2000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Tải lên Văn Bản Hành Chính</h1>
        <p className="text-gray-500 mt-2">Tải văn bản lên hệ thống để AI có thể tóm tắt và đưa vào kho dữ liệu tìm kiếm.</p>
      </div>

      <div className="bg-white rounded-2xl border shadow-sm p-8">
        {!file ? (
          <div 
            className={`border-2 border-dashed rounded-2xl p-16 flex flex-col items-center justify-center transition-all duration-200 ${dragActive ? 'border-admin-blue bg-blue-50' : 'border-gray-300 hover:border-admin-blue hover:bg-gray-50'}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <div className="mb-4 p-4 rounded-full bg-blue-100 text-admin-blue">
              <UploadCloud size={40} />
            </div>
            <p className="text-lg font-medium text-gray-700">Kéo thả file vào đây hoặc</p>
            <label className="mt-2 cursor-pointer relative">
              <span className="text-admin-blue font-semibold hover:underline">Chọn file từ máy tính</span>
              <input 
                type="file" 
                className="hidden" 
                accept=".docx,.pdf"
                onChange={(e) => e.target.files && setFile(e.target.files[0])}
              />
            </label>
            <p className="text-sm text-gray-400 mt-4 text-center">Hỗ trợ định dạng: .DOCX, .PDF. Kích thước tối đa: 20MB.</p>
          </div>
        ) : (
          <div className="border border-gray-200 rounded-2xl p-6 bg-gray-50">
            <div className="flex items-center justify-between mb-6 border-b pb-4">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white rounded-xl shadow-sm">
                  <File size={32} className="text-admin-blue" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-800">{file.name}</h3>
                  <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </div>
              {!uploading && !success && (
                <button onClick={() => setFile(null)} className="p-2 text-gray-400 hover:bg-gray-200 rounded-full transition-colors">
                  <X size={20} />
                </button>
              )}
            </div>

            {uploading && (
              <div className="space-y-3">
                <div className="flex justify-between text-sm font-medium">
                  <span className="text-admin-blue">Đang tải lên & xử lý AI...</span>
                  <span className="text-admin-blue">65%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div className="bg-admin-blue h-2 rounded-full w-[65%] animate-pulse"></div>
                </div>
              </div>
            )}

            {success && (
              <div className="bg-green-50 border border-green-200 text-green-700 p-4 rounded-xl flex items-center gap-3">
                <CheckCircle size={20} />
                <span className="font-medium">Tải lên và tiền xử lý văn bản thành công! Hệ thống RAG đã sẵn sàng.</span>
              </div>
            )}

            {!uploading && !success && (
              <div className="flex justify-end gap-3 mt-6">
                <button onClick={() => setFile(null)} className="px-6 py-2 rounded-lg font-medium text-gray-600 hover:bg-gray-200 transition-colors">
                  Hủy
                </button>
                <button onClick={simulateUpload} className="px-6 py-2 bg-admin-blue text-white rounded-lg font-medium shadow-md hover:bg-blue-800 transition-colors flex items-center gap-2">
                  <UploadCloud size={18} />
                  Bắt đầu tải lên
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;
