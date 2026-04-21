import { useState } from "react";
import {
  FileText,
  File,
  ChevronRight,
  ChevronDown,
  Building2,
  User,
  Globe,
  Download,
  Trash2,
  Paperclip,
  CheckSquare,
  Square,
  BadgeCheck,
  Clock,
} from "lucide-react";

export type FolderDoc = {
  id: number;
  filename: string;
  scope: string;
  is_indexed: boolean;
  uploaded_at: string;
  owner_id?: number;
  department_id?: number;
};

export type FolderTreeData = {
  personal: FolderDoc[];
  department: Record<string, FolderDoc[]>;
  company: FolderDoc[];
};

type SelectMode = "none" | "single" | "multi";

type Props = {
  data: FolderTreeData;
  selectMode?: SelectMode;
  selectedIds?: Set<number>;
  onSelect?: (doc: FolderDoc) => void;
  onDeselect?: (id: number) => void;
  onDownload?: (id: number) => void;
  onDelete?: (id: number, scope: string) => void;
  onAttach?: (doc: FolderDoc) => void;
  attachedIds?: Set<number>;
  /** Ẩn section nếu không có quyền */
  hidePersonal?: boolean;
  hideDepartment?: boolean;
  hideCompany?: boolean;
};

const FILE_ICON_MAP: Record<string, string> = {
  pdf: "text-red-500",
  docx: "text-blue-500",
  doc: "text-blue-400",
  xlsx: "text-green-500",
  txt: "text-gray-400",
};

function fileExt(filename: string) {
  return filename.split(".").pop()?.toLowerCase() ?? "";
}

function FileIcon({ filename }: { filename: string }) {
  const ext = fileExt(filename);
  const colorClass = FILE_ICON_MAP[ext] ?? "text-gray-400";
  return ext === "pdf"
    ? <FileText className={`w-4 h-4 flex-shrink-0 ${colorClass}`} />
    : <File className={`w-4 h-4 flex-shrink-0 ${colorClass}`} />;
}

function IndexBadge({ indexed }: { indexed: boolean }) {
  return indexed ? (
    <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200">
      <BadgeCheck className="w-3 h-3" /> Đã index
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-gray-50 text-gray-400 border border-gray-200">
      <Clock className="w-3 h-3" /> Chưa index
    </span>
  );
}

function DocRow({
  doc,
  selectMode,
  selected,
  attached,
  onSelect,
  onDeselect,
  onDownload,
  onDelete,
  onAttach,
}: {
  doc: FolderDoc;
  selectMode: SelectMode;
  selected: boolean;
  attached: boolean;
  onSelect?: (doc: FolderDoc) => void;
  onDeselect?: (id: number) => void;
  onDownload?: (id: number) => void;
  onDelete?: (id: number, scope: string) => void;
  onAttach?: (doc: FolderDoc) => void;
}) {
  const handleCheck = () => {
    if (selected) onDeselect?.(doc.id);
    else onSelect?.(doc);
  };

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg group transition-colors text-sm
        ${selected ? "bg-blue-50 border border-blue-200" : "hover:bg-gray-50 border border-transparent"}
        ${attached ? "ring-1 ring-emerald-400" : ""}
      `}
    >
      {selectMode !== "none" && (
        <button onClick={handleCheck} className="flex-shrink-0 text-blue-500">
          {selected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4 text-gray-300" />}
        </button>
      )}

      <FileIcon filename={doc.filename} />

      <div className="flex-1 min-w-0">
        <p className="truncate font-medium text-gray-700 text-xs">{doc.filename}</p>
        <p className="text-[10px] text-gray-400">{doc.uploaded_at.slice(0, 10)}</p>
      </div>

      <IndexBadge indexed={doc.is_indexed} />

      {attached && (
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 flex-shrink-0">
          Đã đính kèm
        </span>
      )}

      {/* Action buttons — visible on hover */}
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
        {onAttach && !attached && (
          <button
            onClick={() => onAttach(doc)}
            title="Đính kèm vào chat"
            className="p-1 rounded hover:bg-emerald-100 text-emerald-600"
          >
            <Paperclip className="w-3.5 h-3.5" />
          </button>
        )}
        {onDownload && (
          <button
            onClick={() => onDownload(doc.id)}
            title="Tải xuống"
            className="p-1 rounded hover:bg-blue-100 text-blue-500"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        )}
        {onDelete && (
          <button
            onClick={() => onDelete(doc.id, doc.scope)}
            title="Xóa"
            className="p-1 rounded hover:bg-red-100 text-red-400"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

type RowPropsForSection = {
  selectMode: SelectMode;
  selectedIds?: Set<number>;
  attachedIds?: Set<number>;
  onSelect?: (doc: FolderDoc) => void;
  onDeselect?: (id: number) => void;
  onDownload?: (id: number) => void;
  onDelete?: (id: number, scope: string) => void;
  onAttach?: (doc: FolderDoc) => void;
};

function FolderSection({
  icon,
  label,
  docs,
  defaultOpen = true,
  colorClass = "text-blue-600",
  bgClass = "bg-blue-50",
  selectMode,
  selectedIds = new Set(),
  attachedIds = new Set(),
  onSelect,
  onDeselect,
  onDownload,
  onDelete,
  onAttach,
}: {
  icon: React.ReactNode;
  label: string;
  docs: FolderDoc[];
  defaultOpen?: boolean;
  colorClass?: string;
  bgClass?: string;
} & RowPropsForSection) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen(o => !o)}
        className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg font-semibold text-xs ${colorClass} ${bgClass} hover:opacity-90 transition`}
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        {icon}
        <span className="flex-1 text-left">{label}</span>
        <span className="ml-auto text-[10px] font-normal opacity-70">{docs.length} file</span>
      </button>

      {open && (
        <div className="mt-1 ml-3 space-y-0.5">
          {docs.length === 0 ? (
            <p className="text-xs text-gray-400 px-3 py-2">Chưa có tài liệu</p>
          ) : (
            docs.map(doc => (
              <DocRow
                key={doc.id}
                doc={doc}
                selectMode={selectMode}
                selected={selectedIds?.has(doc.id) ?? false}
                attached={attachedIds?.has(doc.id) ?? false}
                onSelect={onSelect}
                onDeselect={onDeselect}
                onDownload={onDownload}
                onDelete={onDelete}
                onAttach={onAttach}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function FolderTree({
  data,
  selectMode = "none",
  selectedIds = new Set(),
  onSelect,
  onDeselect,
  onDownload,
  onDelete,
  onAttach,
  attachedIds = new Set(),
  hidePersonal = false,
  hideDepartment = false,
  hideCompany = false,
}: Props) {
  const sharedProps = {
    selectMode,
    selectedIds,
    attachedIds,
    onSelect,
    onDeselect,
    onDownload,
    onDelete,
    onAttach,
  };

  const deptEntries = Object.entries(data.department ?? {});

  return (
    <div className="space-y-1">
      {!hidePersonal && (
        <FolderSection
          icon={<User className="w-3.5 h-3.5" />}
          label="Tài liệu cá nhân"
          docs={data.personal ?? []}
          colorClass="text-blue-700"
          bgClass="bg-blue-50"
          {...sharedProps}
        />
      )}

      {!hideDepartment && deptEntries.length > 0 && deptEntries.map(([deptName, docs]) => (
        <FolderSection
          key={deptName}
          icon={<Building2 className="w-3.5 h-3.5" />}
          label={deptName}
          docs={docs}
          colorClass="text-amber-700"
          bgClass="bg-amber-50"
          {...sharedProps}
        />
      ))}

      {!hideDepartment && deptEntries.length === 0 && (
        <FolderSection
          icon={<Building2 className="w-3.5 h-3.5" />}
          label="Tài liệu phòng ban"
          docs={[]}
          colorClass="text-amber-700"
          bgClass="bg-amber-50"
          {...sharedProps}
        />
      )}

      {!hideCompany && (
        <FolderSection
          icon={<Globe className="w-3.5 h-3.5" />}
          label="Tài liệu công ty (SQP)"
          docs={data.company ?? []}
          colorClass="text-violet-700"
          bgClass="bg-violet-50"
          {...sharedProps}
        />
      )}
    </div>
  );
}
