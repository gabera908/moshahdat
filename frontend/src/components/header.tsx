import { Clapperboard } from "lucide-react";
import Link from "next/link";

import SearchBox from "@/components/search-box";
import ThemeToggle from "@/components/theme-toggle";
import { ar } from "@/lib/i18n/ar";

export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur-md dark:border-white/5 dark:bg-surface-dark/85">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2" aria-label={ar.siteName}>
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 text-white shadow-glow">
            <Clapperboard size={19} />
          </span>
          <span className="hidden text-lg font-bold sm:block">{ar.siteName}</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="القائمة الرئيسية">
          <NavLink href="/">{ar.nav.home}</NavLink>
          <NavLink href="/categories">{ar.nav.categories}</NavLink>
          <NavLink href="/playlists">{ar.nav.playlists}</NavLink>
        </nav>

        <div className="mx-auto hidden flex-1 justify-center lg:flex">
          <SearchBox />
        </div>

        <div className="flex items-center gap-1">
          <ThemeToggle />
        </div>
      </div>

      {/* Mobile search row */}
      <div className="border-t border-slate-200/60 px-4 py-2 lg:hidden dark:border-white/5">
        <SearchBox />
      </div>
    </header>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-primary-600 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-primary-400"
    >
      {children}
    </Link>
  );
}
