import { FormEvent, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Briefcase,
  Globe2,
  LayoutDashboard,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { useTracker } from "@/lib/useTracker";

const nav = [
  { to: "/", label: "Home", icon: LayoutDashboard, end: true },
  { to: "/jobs", label: "Jobs", icon: Briefcase, end: false },
  { to: "/countries", label: "Countries", icon: Globe2, end: false },
  { to: "/me", label: "My week", icon: Target, end: false },
];

function pageMeta(pathname: string): { title: string; kicker: string } {
  if (pathname === "/") return { title: "Home", kicker: "Overview" };
  if (pathname === "/jobs") return { title: "Jobs", kicker: "Board" };
  if (pathname.startsWith("/jobs/")) return { title: "Role", kicker: "Jobs" };
  if (pathname === "/me") return { title: "My week", kicker: "Accountability" };
  if (pathname === "/countries") return { title: "Countries", kicker: "Markets" };
  if (pathname.startsWith("/countries/")) return { title: "Market", kicker: "Countries" };
  return { title: "0pening", kicker: "Dashboard" };
}

function Mark() {
  return (
    <svg viewBox="0 0 28 28" width="22" height="22" aria-hidden className="size-[22px]">
      <rect width="28" height="28" rx="7" className="fill-primary/15" />
      <path
        d="M6 20c4-1 7-4.4 7.8-8.4C14.2 14 15.6 16.2 18 17.4c1 .6 2.2 1 3.4 1.1"
        fill="none"
        className="stroke-primary"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="14" cy="9.2" r="1.8" className="fill-primary" />
    </svg>
  );
}

function AppSidebar({ locPath }: { locPath: string }) {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-3 py-3">
        <NavLink to="/" className="flex items-center gap-2.5 rounded-md px-1 py-0.5">
          <Mark />
          <div className="min-w-0 group-data-[collapsible=icon]:hidden">
            <div className="font-heading text-lg leading-none tracking-tight">0pening</div>
            <div className="mt-0.5 text-[11px] text-muted-foreground">by AskTheHR</div>
          </div>
        </NavLink>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {nav.map((item) => {
                const isActive = item.end
                  ? locPath === item.to
                  : locPath === item.to || locPath.startsWith(`${item.to}/`);
                return (
                  <SidebarMenuItem key={item.to}>
                    <SidebarMenuButton asChild isActive={isActive} tooltip={item.label}>
                      <NavLink to={item.to} end={item.end}>
                        <item.icon />
                        <span>{item.label}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="px-3 pb-3">
        <p className="px-1 text-[11px] leading-relaxed text-muted-foreground group-data-[collapsible=icon]:hidden">
          August 2026 · remote-first
          <br />
          Ten countries. No account.
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}

export function Layout() {
  const { thisWeek, target, nickname } = useTracker();
  const loc = useLocation();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const meta = pageMeta(loc.pathname);
  const pct = Math.min(100, Math.round((thisWeek / Math.max(target, 1)) * 100));

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    const next = q.trim();
    navigate(next ? `/jobs?q=${encodeURIComponent(next)}` : "/jobs");
  };

  return (
    <SidebarProvider>
      <AppSidebar locPath={loc.pathname} />
      <SidebarInset>
        <header className="sticky top-0 z-20 flex h-12 shrink-0 items-center gap-3 border-b bg-background/80 px-3 backdrop-blur-md">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-4" />
          <div className="min-w-0">
            <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {meta.kicker}
            </div>
            <div className="truncate text-sm font-medium leading-none">{meta.title}</div>
          </div>
          <form onSubmit={onSearch} className="ml-2 hidden min-w-0 flex-1 md:block">
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search title or company…"
              className="h-8 max-w-md"
              aria-label="Search jobs"
            />
          </form>
          <div className="ml-auto flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
              <NavLink to="/me" className="gap-2">
                <span className="text-muted-foreground">
                  {nickname ? nickname : "This week"}
                </span>
                <span className="tabular-nums font-medium">
                  {thisWeek}/{target}
                </span>
                <Progress value={pct} className="hidden w-16 md:flex" />
              </NavLink>
            </Button>
          </div>
        </header>
        <div className="flex-1">
          <div className="mx-auto w-full max-w-[1120px] px-4 py-6 md:px-8 md:py-8">
            <Outlet />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
