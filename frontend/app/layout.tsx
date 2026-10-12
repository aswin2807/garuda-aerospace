import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Garuda Aerospace Drone AI // Command Centre",
  description: "Garuda Aerospace AI-powered real-time drone navigation, FOD detection, and runway light fault analysis platform",
};


export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#FFFFFF] text-[#111827] antialiased overflow-hidden">
        {children}
      </body>
    </html>
  );
}
