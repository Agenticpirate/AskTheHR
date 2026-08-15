import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { Menu } from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { applyTheme, readTheme } from "@/lib/theme";

const nav = [
  { href: "/#how", label: "How it works" },
  { href: "/#product", label: "Product" },
  { href: "/#pricing", label: "Pricing" },
  { href: "/#faq", label: "FAQ" },
];

export function MarketingLayout() {
  const loc = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    applyTheme(readTheme());
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [loc.pathname, loc.hash]);

  useEffect(() => {
    if (!loc.hash) return;
    const id = loc.hash.replace("#", "");
    const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: "auto", block: "start" });
  }, [loc.hash]);

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:ring-1 focus:ring-border"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 w-full max-w-[1120px] items-center gap-3 px-5 md:px-12">
          <NavLink to="/" className="flex items-center gap-2.5">
            <BrandMark />
            <span className="text-lg leading-none tracking-tight">AskTheHR</span>
          </NavLink>
          <nav aria-label="Marketing" className="ml-6 hidden items-center gap-5 md:flex">
            {nav.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                {item.label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
              <Link to="/app">Open app</Link>
            </Button>
            <Button size="sm" asChild className="hidden sm:inline-flex">
              <Link to="/me">Start Cadence</Link>
            </Button>
            <ThemeToggle />
            <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
                  <Menu />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-[min(100%,20rem)]">
                <SheetHeader>
                  <SheetTitle>AskTheHR</SheetTitle>
                </SheetHeader>
                <nav aria-label="Mobile" className="flex flex-col gap-1 px-4">
                  {nav.map((item) => (
                    <SheetClose asChild key={item.href}>
                      <a
                        href={item.href}
                        className="rounded-md px-2 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
                      >
                        {item.label}
                      </a>
                    </SheetClose>
                  ))}
                  <SheetClose asChild>
                    <Link
                      to="/app"
                      className="rounded-md px-2 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      Open app
                    </Link>
                  </SheetClose>
                  <SheetClose asChild>
                    <Link
                      to="/jobs"
                      className="rounded-md px-2 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      0penings
                    </Link>
                  </SheetClose>
                  <Button asChild className="mt-3">
                    <SheetClose asChild>
                      <Link to="/me">Start Cadence</Link>
                    </SheetClose>
                  </Button>
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t">
        <div className="mx-auto grid w-full max-w-[1120px] gap-10 px-5 py-12 md:grid-cols-4 md:px-12">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2.5">
              <BrandMark />
              <span className="text-lg leading-none tracking-tight">AskTheHR</span>
            </div>
            <p className="max-w-xs text-sm text-muted-foreground">
              Cadence is paid accountability. 0penings is the free employer-direct board inside it.
            </p>
          </div>
          <FooterCol
            title="Product"
            links={[
              { to: "/#how", label: "How Cadence works", hash: true },
              { to: "/#product", label: "Product", hash: true },
              { to: "/#pricing", label: "Pricing", hash: true },
              { to: "/jobs", label: "0penings" },
              { to: "/app", label: "App home" },
            ]}
          />
          <FooterCol
            title="Workspace"
            links={[
              { to: "/me", label: "Me" },
              { to: "/streak", label: "Cadence" },
              { to: "/board", label: "Board" },
              { to: "/countries", label: "Countries" },
              { to: "/join", label: "Join" },
            ]}
          />
          <FooterCol
            title="Company"
            links={[
              { to: "/terms", label: "Terms" },
              { to: "mailto:support@0pening.com", label: "support@0pening.com", external: true },
            ]}
          />
        </div>
        <div className="border-t">
          <div className="mx-auto flex w-full max-w-[1120px] flex-wrap items-center justify-between gap-3 px-5 py-5 text-xs text-muted-foreground md:px-12">
            <span>AskTheHR · Cadence · 0penings</span>
            <span>No account required to start.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FooterCol({
  title,
  links,
}: {
  title: string;
  links: { to: string; label: string; hash?: boolean; external?: boolean }[];
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="micro">{title}</div>
      <ul className="flex flex-col gap-2 text-sm">
        {links.map((item) => (
          <li key={item.to}>
            {item.external || item.hash ? (
              <a href={item.to} className="text-muted-foreground hover:text-foreground">
                {item.label}
              </a>
            ) : (
              <Link to={item.to} className="text-muted-foreground hover:text-foreground">
                {item.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
