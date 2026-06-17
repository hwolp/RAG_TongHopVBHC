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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TagList, type DocumentTag } from "./TagSelector";

export type FolderDoc = {
  id: number;
  filename: string;
  scope: string;
  is_indexed: boolean;
  index_status?: "indexed" | "not_indexed" | "queued" | "running" | "failed";
  uploaded_at: string;
  owner_id?: number;
  department_id?: number;
  tags?: DocumentTag[];
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
  canDelete?: (doc: FolderDoc) => boolean;
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

function IndexBadge({ doc }: { doc: FolderDoc }) {
  const status = doc.index_status || (doc.is_indexed ? "indexed" : "not_indexed");
  const labels: Record<string, string> = {
    indexed: "Đã index",
    queued: "Chờ index",
    running: "Đang index",
    failed: "Index lỗi",
    not_indexed: "Chưa index",
  };
  const Icon = status === "indexed" ? BadgeCheck : Clock;
  const variant = status === "indexed" ? "success" : status === "queued" || status === "running" ? "warning" : status === "failed" ? "destructive" : "secondary";
  return (
    <Badge variant={variant} className="gap-1 px-1.5 py-0.5 text-[10px]">
      <Icon className="w-3 h-3" /> {labels[status] || labels.not_indexed}
    </Badge>
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
  canDelete,
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
  canDelete?: (doc: FolderDoc) => boolean;
  onAttach?: (doc: FolderDoc) => void;
}) {
  const handleCheck = () => {
    if (selected) onDeselect?.(doc.id);
    else onSelect?.(doc);
  };

  return (
    <div
      className={cn(
        "group flex items-center gap-2 rounded-md border border-transparent px-3 py-2 text-sm transition-colors hover:border-border hover:bg-muted/50",
        selected && "border-primary/30 bg-primary/10 text-primary",
        attached && "ring-2 ring-emerald-400/50",
      )}
    >
      {selectMode !== "none" && (
        <Button type="button" variant="ghost" size="icon-sm" onClick={handleCheck} className="h-7 w-7 flex-shrink-0 text-primary">
          {selected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4 text-gray-300" />}
        </Button>
      )}

      <FileIcon filename={doc.filename} />

      <div className="min-w-0 flex-1">
        <p className="break-all text-xs font-medium leading-5 text-foreground">{doc.filename}</p>
        <p className="text-[10px] text-muted-foreground">{doc.uploaded_at.slice(0, 10)}</p>
        <TagList tags={doc.tags} className="mt-1" />
      </div>

      <IndexBadge doc={doc} />

      {attached && (
        <Badge variant="success" className="flex-shrink-0 px-1.5 py-0.5 text-[10px]">
          Đã đính kèm
        </Badge>
      )}

      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
        {onAttach && !attached && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={() => onAttach(doc)}
            title="Đính kèm vào chat"
            className="h-7 w-7 text-emerald-600"
          >
            <Paperclip className="w-3.5 h-3.5" />
          </Button>
        )}
        {onDownload && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={() => onDownload(doc.id)}
            title="Tải xuống"
            className="h-7 w-7 text-primary"
          >
            <Download className="w-3.5 h-3.5" />
          </Button>
        )}
        {onDelete && (!canDelete || canDelete(doc)) && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={() => onDelete(doc.id, doc.scope)}
            title="Xóa"
            className="h-7 w-7 text-destructive"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
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
  canDelete?: (doc: FolderDoc) => boolean;
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
  canDelete,
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
    <Card className="glass-panel mb-2 overflow-hidden p-1">
      <Button
        type="button"
        variant="ghost"
        onClick={() => setOpen(o => !o)}
        className={cn("h-10 w-full justify-start px-3 text-xs font-semibold", colorClass, bgClass)}
      >
        {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        {icon}
        <span className="flex-1 text-left">{label}</span>
        <Badge variant="secondary" className="ml-auto px-2 py-0 text-[10px]">{docs.length} file</Badge>
      </Button>

      {open && (
        <div className="ml-3 mt-1 space-y-1 border-l border-border/70 pl-2">
          {docs.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">Chưa có tài liệu</p>
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
                canDelete={canDelete}
                onAttach={onAttach}
              />
            ))
          )}
        </div>
      )}
    </Card>
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
  canDelete,
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
    canDelete,
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
