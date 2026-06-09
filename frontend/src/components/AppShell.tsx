import { BookOpen, FileQuestion, LayoutDashboard, LibraryBig, UploadCloud } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/upload", label: "Upload", icon: UploadCloud },
  { to: "/documents", label: "Documents", icon: LibraryBig },
  { to: "/generate-test", label: "Tests", icon: FileQuestion },
  { to: "/study", label: "Study", icon: BookOpen }
];

export function AppShell() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-white/94 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div>
            <h1 className="text-lg font-bold text-ink">ExamPrep RAG</h1>
            <p className="text-xs font-medium text-slate-500">AI-Powered PDF Study Assistant</p>
          </div>
          <nav className="flex gap-2 overflow-x-auto pb-1 lg:pb-0">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      "inline-flex min-h-10 shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition",
                      isActive ? "bg-ink text-white" : "text-slate-600 hover:bg-slate-100 hover:text-ink"
                    ].join(" ")
                  }
                >
                  <Icon size={17} aria-hidden="true" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}

