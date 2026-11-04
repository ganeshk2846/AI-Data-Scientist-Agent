import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AI for BI — verified analysis",
    // Every screen names itself in the tab, and every one of them ends in the
    // product's name.
    template: "%s",
  },
  description:
    "Ask a business question and get verified analysis: headline figures with their uncertainty, a chart, the rows, and the SQL that produced every number.",
};

/**
 * Applied before paint so the first frame is already in the right theme.
 * Gold reads as light falling on dark material, so dark is the default; the
 * viewer's own choice always wins once they have made one.
 */
const THEME_BOOTSTRAP = `(function(){try{var s=localStorage.getItem("aibi-theme");var m=window.matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.setAttribute("data-theme",s==="light"||s==="dark"?s:"dark");}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preload" href="/fonts/Geist-Regular.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link rel="preload" href="/fonts/GeistMono-Regular.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
        <link
          rel="preload"
          href="/fonts/InstrumentSerif-Regular.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
