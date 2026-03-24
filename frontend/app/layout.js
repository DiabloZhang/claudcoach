import { Geist } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";

const geist = Geist({ subsets: ["latin"] });

export const metadata = {
  title: "TriCoach",
  description: "AI-Powered Triathlon Training Assistant",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh">
      <body className={`${geist.className} bg-gray-950 text-gray-100 min-h-screen`}>
        <Nav />
        <main className="max-w-6xl mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
