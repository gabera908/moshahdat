import Link from "next/link";

export default function NotFound() {
  return (
    <div className="grid min-h-[50vh] place-items-center text-center">
      <div>
        <p className="text-6xl font-black text-primary-500/30">404</p>
        <h1 className="mt-3 text-xl font-bold">الصفحة غير موجودة</h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          قد يكون المحتوى حُذف أو الرابط خاطئ.
        </p>
        <Link
          href="/"
          className="mt-5 inline-block rounded-full bg-primary-500 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-primary-600"
        >
          العودة للرئيسية
        </Link>
      </div>
    </div>
  );
}
