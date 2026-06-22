"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/upload", label: "Upload" },
  { href: "/goals", label: "Goals" },
  { href: "/chat", label: "Chat" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { signOut } = useAuth();

  return (
    <nav className="flex h-screen w-56 flex-col border-r border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-5">
        <p className="text-sm font-semibold text-gray-900">Personal Finance AI</p>
        <p className="text-xs text-gray-500">Household review</p>
      </div>
      <ul className="flex-1 space-y-1 px-2 py-4">
        {NAV_ITEMS.map((item) => {
          const active = pathname?.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`block rounded-md px-3 py-2 text-sm font-medium ${
                  active
                    ? "bg-gray-900 text-white"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="border-t border-gray-200 px-4 py-4">
        <button
          onClick={() => signOut()}
          className="text-xs font-medium text-gray-500 hover:text-gray-900"
        >
          Log out
        </button>
      </div>
    </nav>
  );
}
