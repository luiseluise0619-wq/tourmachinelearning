import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "FestCast — 축제 기획 AI",
  description: "데이터로 축제 흥행을 예보하고 기획을 최적화하는 AI SaaS",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
