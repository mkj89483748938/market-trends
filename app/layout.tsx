import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OC Market Trends",
  description: "Orange County real estate market trends for agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
