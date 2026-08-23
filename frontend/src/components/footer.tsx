import { Clapperboard } from "lucide-react";
import Link from "next/link";

import { ar } from "@/lib/i18n/ar";

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-16 border-t border-slate-200/70 bg-white dark:border-white/5 dark:bg-surface-card/40">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 text-white">
              <Clapperboard size={16} />
            </span>
            <span className="font-bold">{ar.siteName}</span>
          </div>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-slate-500 dark:text-slate-400">
            {ar.footer.about}
          </p>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold">{ar.footer.sections}</h3>
          <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
            <li><Link className="hover:text-primary-500" href="/">{ar.nav.home}</Link></li>
            <li><Link className="hover:text-primary-500" href="/categories">{ar.nav.categories}</Link></li>
            <li><Link className="hover:text-primary-500" href="/playlists">{ar.nav.playlists}</Link></li>
            <li><Link className="hover:text-primary-500" href="/search">{ar.nav.latest}</Link></li>
          </ul>
        </div>

        <div />
      </div>
      <div className="border-t border-slate-200/60 py-4 text-center text-xs text-slate-400 dark:border-white/5">
        © {year} {ar.siteName} — {ar.footer.rights}
      </div>
    </footer>
  );
}
