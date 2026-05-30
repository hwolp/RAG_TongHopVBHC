import { useEffect, useMemo, useState } from "react";
import { Plus, Tag, X } from "lucide-react";
import api from "../api";

export type DocumentTag = {
  id: number;
  name: string;
};

type Props = {
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
  compact?: boolean;
};

export default function TagPicker({ selectedIds, onChange, disabled = false, compact = false }: Props) {
  const [tags, setTags] = useState<DocumentTag[]>([]);
  const [newTag, setNewTag] = useState("");
  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);

  const fetchTags = async () => {
    const response = await api.get<DocumentTag[]>("/tags");
    setTags(response.data);
  };

  useEffect(() => {
    void fetchTags();
  }, []);

  const toggleTag = (tagId: number) => {
    if (disabled) return;
    if (selected.has(tagId)) {
      onChange(selectedIds.filter((id) => id !== tagId));
      return;
    }
    onChange([...selectedIds, tagId]);
  };

  const createTag = async () => {
    const name = newTag.trim();
    if (!name || disabled) return;
    const response = await api.post("/employee/tags", { name });
    const tagId = response.data.id;
    setNewTag("");
    await fetchTags();
    if (tagId && !selected.has(tagId)) {
      onChange([...selectedIds, tagId]);
    }
  };

  return (
    <div className={compact ? "space-y-2" : "space-y-3"}>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => {
          const active = selected.has(tag.id);
          return (
            <button
              type="button"
              key={tag.id}
              onClick={() => toggleTag(tag.id)}
              disabled={disabled}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition disabled:opacity-60 ${
                active
                  ? "border-blue-200 bg-blue-50 text-blue-700"
                  : "border-gray-200 bg-white text-gray-600 hover:border-blue-200"
              }`}
            >
              <Tag className="h-3 w-3" />
              {tag.name}
              {active && <X className="h-3 w-3" />}
            </button>
          );
        })}
        {tags.length === 0 && (
          <span className="text-xs text-gray-400">Chưa có tag nào</span>
        )}
      </div>

      <div className="flex gap-2">
        <input
          value={newTag}
          onChange={(event) => setNewTag(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && void createTag()}
          disabled={disabled}
          className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm"
          placeholder="Tạo tag mới..."
        />
        <button
          type="button"
          onClick={() => void createTag()}
          disabled={disabled || !newTag.trim()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-60"
        >
          <Plus className="h-4 w-4" />
          Thêm
        </button>
      </div>
    </div>
  );
}
