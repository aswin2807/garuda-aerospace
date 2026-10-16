import "./globals.css";
import type { Metadata } from "next";
import { AuthGuard } from "../components/auth/AuthGuard";

export const metadata: Metadata = {
  title: "Garuda Aerospace",
  description:
    "Garuda Aerospace AI-powered real-time drone navigation, FOD detection, and runway light fault analysis platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#FFFFFF] text-[#111827] antialiased overflow-x-hidden">
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}
