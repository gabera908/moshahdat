import { cn } from "@/lib/utils";

export function CardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl bg-white dark:bg-surface-card">
      <div className="skeleton aspect-video rounded-none" />
      <div className="space-y-2 p-3">
        <div className="skeleton h-4 w-11/12" />
        <div className="skeleton h-3 w-2/3" />
      </div>
    </div>
  );
}

export function GridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export function SectionTitle({
  title,
  action,
}: {
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className={cn("mb-4 flex items-center justify-between")}>
      <h2 className="flex items-center gap-2 text-lg font-bold sm:text-xl">
        <span className="h-6 w-1.5 rounded-full bg-gradient-to-b from-primary-400 to-primary-600" />
        {title}
      </h2>
      {action}
    </div>
  );
}

export function EmptyState({
  title,
  subtitle,
  icon,
}: {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="grid place-items-center rounded-2xl border border-dashed border-slate-300 py-16 text-center dark:border-white/10">
      {icon && <div className="mb-3 text-slate-300 dark:text-slate-600">{icon}</div>}
      <p className="font-semibold">{title}</p>
      {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
    </div>
  );
}

export function PaginationLinks({
  page,
  pages,
  buildHref,
}: {
  page: number;
  pages: number;
  buildHref: (p: number) => string;
}) {
  if (pages <= 1) return null;

  const window = 2;
  const numbers: number[] = [];
  for (let p = Math.max(1, page - window); p <= Math.min(pages, page + window); p++) {
    numbers.push(p);
  }

  const btn =
    "min-w-[2.25rem] rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-40";

  return (
    <nav className="mt-8 flex items-center justify-center gap-1.5" aria-label="ترقيم الصفحات">
      <a
        href={buildHref(page - 1)}
        aria-disabled={page <= 1}
        className={cn(btn, "bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10", page <= 1 && "pointer-events-none opacity-40")}
      >
        السابق
      </a>
      {numbers[0] > 1 && <span className="px-1 text-slate-400">…</span>}
      {numbers.map((p) => (
        <a
          key={p}
          href={buildHref(p)}
          aria-current={p === page ? "page" : undefined}
          className={cn(
            btn,
            p === page
              ? "bg-primary-500 text-white shadow-glow"
              : "bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10",
          )}
        >
          {p}
        </a>
      ))}
      {numbers[numbers.length - 1] < pages && <span className="px-1 text-slate-400">…</span>}
      <a
        href={buildHref(page + 1)}
        aria-disabled={page >= pages}
        className={cn(btn, "bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10", page >= pages && "pointer-events-none opacity-40")}
      >
        التالي
      </a>
    </nav>
  );
}
