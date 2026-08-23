import type { Metadata } from "next";
import { Suspense } from "react";

import Footer from "@/components/footer";
import Header from "@/components/header";
import Providers from "@/components/providers";
import { SITE_NAME, SITE_URL } from "@/lib/api";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — منصة عرض الفيديوهات`,
    template: `%s | ${SITE_NAME}`,
  },
  description: "منصة عربية لعرض وإدارة الفيديوهات: وثائقيات، تقارير، دورات وقوائم تشغيل منظمة.",
  openGraph: {
    type: "website",
    locale: "ar",
    siteName: SITE_NAME,
  },
  twitter: { card: "summary_large_image" },
};

const themeInit = `
(function(){try{
  var t = localStorage.getItem('theme') || 'dark';
  if (t === 'dark') document.documentElement.classList.add('dark');
}catch(e){document.documentElement.classList.add('dark');}})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap"
          rel="stylesheet"
        />
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="flex min-h-screen flex-col font-sans">
        <Providers>
          <Suspense>
            <Header />
          </Suspense>
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
