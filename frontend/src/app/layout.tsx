import "./globals.css";

import type { Metadata } from "next";
import localFont from "next/font/local";
import { Handjet, JetBrains_Mono } from "next/font/google";

// Body sans (clean grotesque) — kept from the existing setup.
const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-sans",
  weight: "100 900",
});
// Pixel / bitmap display font for headings + big numbers.
const handjet = Handjet({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});
// Monospace for transcripts, IDs, timestamps, config.
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Аудиобейдж",
  description: "AI-анализ звонков менеджеров",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="dark">
      <body
        className={`${geistSans.variable} ${handjet.variable} ${jetbrainsMono.variable}`}
      >
        {children}
      </body>
    </html>
  );
}
