import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Battery Opportunity Scanner",
  description: "Emerging battery startup opportunities, before they're obvious.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-6xl px-6 py-10">{children}</div>
      </body>
    </html>
  );
}
