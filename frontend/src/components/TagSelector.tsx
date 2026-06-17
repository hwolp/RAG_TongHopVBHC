import { useEffect, useMemo, useState } from "react";
import { Tag } from "lucide-react";
import api from "../api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type DocumentTag = {
  id: number;
  name: string;
};

type Props = {
  value: number[];
  onChange: (tagIds: number[]) => void;
  className?: string;
  compact?: boolean;
};

export function appendTagIds(formData: FormData, tagIds: number[]) {
  tagIds.forEach((tagId) => formData.append("tag_ids", String(tagId)));
}

export function TagList({
  tags,
  className,
  showEmpty = false,
  emptyLabel = "Chưa gắn tag",
}: {
  tags?: DocumentTag[];
  className?: string;
  showEmpty?: boolean;
  emptyLabel?: string;
}) {
  if (!tags?.length) {
    if (!showEmpty) return null;
    return (
      <Badge variant="outline" className={cn("gap-1 text-muted-foreground", className)}>
        <Tag className="h-3 w-3" />
        {emptyLabel}
      </Badge>
    );
  }
  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {tags.map((tag) => (
        <Badge key={tag.id} variant="secondary" className="gap-1">
          <Tag className="h-3 w-3" />
          {tag.name}
        </Badge>
      ))}
    </div>
  );
}

export default function TagSelector({ value, onChange, className, compact = false }: Props) {
  const [tags, setTags] = useState<DocumentTag[]>([]);

  useEffect(() => {
    let mounted = true;
    api.get("/tags")
      .then((response) => {
        if (mounted) setTags(response.data ?? []);
      })
      .catch(() => {
        if (mounted) setTags([]);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const selected = useMemo(() => new Set(value), [value]);

  const toggle = (tagId: number) => {
    if (selected.has(tagId)) {
      onChange(value.filter((id) => id !== tagId));
      return;
    }
    onChange([...value, tagId]);
  };

  if (tags.length === 0) {
    return (
      <div className={cn("rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground", className)}>
        Chưa có tag để gắn.
      </div>
    );
  }

  return (
    <div className={cn("space-y-2", className)}>
      {!compact && (
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <Tag className="h-3.5 w-3.5" />
          Gắn tag cho tài liệu
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => {
          const active = selected.has(tag.id);
          return (
            <Button
              key={tag.id}
              type="button"
              variant={active ? "default" : "outline"}
              size="sm"
              onClick={() => toggle(tag.id)}
              className={cn("h-8 rounded-full px-3", compact && "h-7 px-2 text-xs")}
            >
              {tag.name}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
