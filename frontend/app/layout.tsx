import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KHULOUD AI OS",
  description: "Local-first multi-agent company operating system for Khuloud Perfumes"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
