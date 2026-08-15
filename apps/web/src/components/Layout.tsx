import { FormEvent, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Briefcase,
  Flame,
  Globe2,
  LayoutDashboard,
  Target,
  Trophy,
  UserPlus,
} from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { publishEntry } from "@/lib/leaderboard";
import { fireDailyReminder, shouldFireReminder, wallClock } from "@/lib/reminders";
import { applyTheme, readTheme } from "@/lib/theme";
import { useTracker } from "@/lib/useTracker";

const nav = [
  { to: "/", label: "Home", icon: LayoutDashboard, end: true },
  { to: "/jobs", label: "Jobs", icon: Briefcase, end: false },
  { to: "/countries", label: "Countries", icon: Globe2, end: false },
  { to: "/me", label: "Me", icon: Target, end: false },
  { to: "/streak", label: "Cadence", icon: Flame, end: false },
  { to: "/board", label: "Board", icon: Trophy, end: false },
];

const joinItem = { to: "/join", label: "Join", icon: UserPlus, end: true };

function pageMeta(pathname: string): { title: string; kicker: string } {
  if (pathname === "/") return { title: "Home", kicker: "Overview" };
  if (pathname === "/jobs") return { title: "Jobs", kicker: "Board" };
  if (pathname.startsWith("/jobs/")) return { title: "Role", kicker: "Jobs" };
  if (pathname === "/me") return { title: "Me", kicker: "Command" };
  if (pathname === "/streak") return { title: "Cadence", kicker: "Discipline" };
  if (pathname === "/board") return { title: "Board", kicker: "Public" };
  if (pathname === "/countries") return { title: "Countries", kicker: "Markets" };
  if (pathname.startsWith("/countries/")) return { title: "Market", kicker: "Countries" };
  if (pathname === "/join") return { title: "Join", kicker: "Name" };
  if (pathname === "/terms") return { title: "Terms", kicker: "Legal" };
  return { title: "0pening", kicker: "Dashboard" };
}

function Mark() {
  return (
    <svg viewBox="0 0 28 28" width="22" height="22" aria-hidden className="size-[22px]">
      <rect width="28" height="28" rx="6" className="fill-foreground/10" />
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

function AppSidebar({ locPath, showJoin }: { locPath: string; showJoin: boolean }) {
  const items = showJoin ? [nav[0], joinItem, ...nav.slice(1)] : nav;
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-3 py-3">
        <NavLink to="/" className="flex items-center gap-2.5 rounded-md px-1 py-0.5">
          <Mark />
          <div className="min-w-0 group-data-[collapsible=icon]:hidden">
            <div className="text-lg leading-none tracking-tight">0pening</div>
            <div className="mt-0.5 text-[11px] text-muted-foreground">by AskTheHR</div>
          </div>
        </NavLink>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
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
        <NavLink
          to="/terms"
          className="mt-2 px-1 text-[11px] text-muted-foreground underline-offset-4 hover:text-foreground hover:underline group-data-[collapsible=icon]:hidden"
        >
          Terms
        </NavLink>
      </SidebarFooter>
    </Sidebar>
  );
}

export function Layout() {
  const tracker = useTracker();
  const loc = useLocation();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const meta = pageMeta(loc.pathname);
  const fullBleed = loc.pathname === "/me" && !tracker.track;

  useEffect(() => {
    applyTheme(readTheme());
  }, []);

  useEffect(() => {
    const track = tracker.track;
    if (!tracker.published || !tracker.nickname.trim() || !track) return;
    const handle = window.setTimeout(() => {
      void publishEntry({
        id: tracker.publicId,
        nickname: tracker.nickname.trim(),
        track,
        dailyStreak: tracker.dailyStreak,
        weeklyStreak: tracker.streak,
        xp: tracker.xp,
        level: tracker.level.name,
        publishedAt: new Date().toISOString(),
      });
    }, 700);
    return () => window.clearTimeout(handle);
  }, [
    tracker.published,
    tracker.nickname,
    tracker.track,
    tracker.dailyStreak,
    tracker.streak,
    tracker.xp,
    tracker.level.name,
    tracker.publicId,
  ]);

  useEffect(() => {
    const tick = () => {
      if (!shouldFireReminder(new Date(), tracker.reminder)) return;
      const { date } = wallClock(new Date(), tracker.reminder.timezone);
      void fireDailyReminder({
        reminder: tracker.reminder,
        plan: tracker.plan,
        whatsapp: tracker.whatsapp,
      });
      tracker.markReminderFired(date);
    };
    tick();
    const id = window.setInterval(tick, 20_000);
    const onVis = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [tracker.reminder, tracker.plan, tracker.whatsapp, tracker.markReminderFired]);

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    const next = q.trim();
    navigate(next ? `/jobs?q=${encodeURIComponent(next)}` : "/jobs");
  };

  return (
    <SidebarProvider>
      <AppSidebar locPath={loc.pathname} showJoin={!tracker.profile.username} />
      <SidebarInset>
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-4" />
          <div className="min-w-0">
            <div className="micro">{meta.kicker}</div>
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
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
              <NavLink to="/streak" className="gap-2">
                <span className="text-muted-foreground">
                  {tracker.profile.username
                    ? `@${tracker.profile.username}`
                    : tracker.nickname
                      ? tracker.nickname
                      : "Cadence"}
                </span>
                <span className="font-mono tabular-nums font-medium">{tracker.dailyStreak}</span>
              </NavLink>
            </Button>
            <ThemeToggle />
          </div>
        </header>
        <div className="flex-1">
          {fullBleed ? (
            <Outlet />
          ) : (
            <div
              className={
                loc.pathname === "/streak"
                  ? "mx-auto w-full max-w-[1120px] px-5 py-6 md:px-12 md:py-8"
                  : "mx-auto w-full max-w-[1120px] px-5 py-10 md:px-12 md:py-16"
              }
            >
              <Outlet />
            </div>
          )}
        </div>
        <footer className="mt-auto border-t px-5 py-5 md:px-12">
          <div className="mx-auto flex w-full max-w-[1120px] items-center justify-between gap-4 text-xs text-muted-foreground">
            <span>0pening · AskTheHR</span>
            <NavLink to="/terms" className="hover:text-foreground">
              Terms
            </NavLink>
          </div>
        </footer>
      </SidebarInset>
    </SidebarProvider>
  );
}
