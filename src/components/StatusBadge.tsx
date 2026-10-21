import { Badge } from "@/components/ui/badge";
import { statusLabel } from "@/lib/format";

const STATUS_STYLES: Record<string, string> = {
  agendado: "bg-accent-soft text-primary",
  em_andamento: "bg-primary text-primary-foreground",
  concluido: "bg-secondary text-primary",
  cancelado: "bg-destructive/10 text-destructive",
  ativa: "bg-accent-soft text-primary",
  cancelada: "bg-destructive/10 text-destructive",
};

export function StatusBadge({ status, className = "" }: { status: string; className?: string }) {
  return (
    <Badge variant="secondary" className={`shrink-0 ${STATUS_STYLES[status] ?? ""} ${className}`}>
      {statusLabel(status)}
    </Badge>
  );
}
