import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { JobTable } from "@/components/JobTable";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { COUNTRIES } from "@/data/countries";
import { formatCount } from "@/lib/format";
import { matchesFilters, type JobFilters } from "@/lib/jobs";
import { useJobs } from "@/lib/useJobs";

const PAGE = 20;

function readFilters(sp: URLSearchParams): JobFilters {
  const work = sp.get("work");
  return {
    q: sp.get("q") ?? "",
    country: sp.get("country") ?? "",
    place: sp.get("place") ?? "",
    work: work === "remote" || work === "onsite" ? work : "all",
  };
}

function countryLabel(value: string): string {
  if (!value) return "All countries";
  if (value === "worldwide") return "Worldwide";
  return value;
}

function workLabel(value: JobFilters["work"]): string {
  if (value === "remote") return "Remote";
  if (value === "onsite") return "On-site";
  return "Remote + on-site";
}

export function Jobs() {
  const { data, error, loading, loadingMore } = useJobs(true);
  const [sp, setSp] = useSearchParams();
  const filters = readFilters(sp);
  const page = Math.max(1, Number(sp.get("page") || 1) || 1);

  const set = (patch: Record<string, string>) => {
    const next = new URLSearchParams(sp);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in patch)) next.delete("page");
    setSp(next, { replace: true });
  };

  const jobs = data?.jobs ?? [];
  const filtered = useMemo(
    () => jobs.filter((j) => matchesFilters(j, filters)),
    [jobs, filters.q, filters.country, filters.place, filters.work],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const safePage = Math.min(page, pages);
  const slice = filtered.slice((safePage - 1) * PAGE, safePage * PAGE);

  return (
    <>
      <PageHeader
        eyebrow="Board"
        title="Jobs"
        description={
          data
            ? `${formatCount(data.shown)} listings on this board${
                data.shown < data.total ? ` of ${formatCount(data.total)} collected` : ""
              }.`
            : "Search, then narrow by country, city, and remote."
        }
      />

      <div className="mb-4 flex flex-col gap-2 rounded-xl bg-card p-3 ring-1 ring-foreground/10 md:flex-row md:items-center">
        <Input
          value={filters.q}
          placeholder="Search title or company…"
          aria-label="Search"
          onChange={(e) => set({ q: e.target.value })}
          className="md:max-w-xs"
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="justify-between md:w-40">
              {countryLabel(filters.country)}
              <ChevronDown className="size-3.5 opacity-60" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuItem onClick={() => set({ country: "" })}>All countries</DropdownMenuItem>
            {COUNTRIES.map((c) => (
              <DropdownMenuItem key={c} onClick={() => set({ country: c })}>
                {c}
              </DropdownMenuItem>
            ))}
            <DropdownMenuItem onClick={() => set({ country: "worldwide" })}>
              Worldwide / unspecified
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Input
          value={filters.place}
          placeholder="City or state"
          aria-label="City or state"
          onChange={(e) => set({ place: e.target.value })}
          className="md:max-w-[180px]"
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="justify-between md:w-40">
              {workLabel(filters.work)}
              <ChevronDown className="size-3.5 opacity-60" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-44">
            <DropdownMenuItem onClick={() => set({ work: "" })}>Remote + on-site</DropdownMenuItem>
            <DropdownMenuItem onClick={() => set({ work: "remote" })}>Remote</DropdownMenuItem>
            <DropdownMenuItem onClick={() => set({ work: "onsite" })}>On-site</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => set({ q: "", country: "", place: "", work: "" })}
        >
          Reset
        </Button>
      </div>

      <div className="mb-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {loading ? "Loading…" : `${formatCount(filtered.length)} roles`}
          {loadingMore ? " · loading the rest of the board…" : ""}
          {error ? ` · ${error}` : ""}
        </span>
        <span>
          Page {safePage} of {pages}
        </span>
      </div>

      <JobTable
        jobs={slice}
        empty={error ? error : "Nothing matches those filters. Widen country or search."}
      />

      {pages > 1 ? (
        <div className="mt-4 flex items-center justify-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={safePage <= 1}
            onClick={() => set({ page: String(safePage - 1) })}
          >
            Prev
          </Button>
          <span className="min-w-16 text-center text-xs text-muted-foreground">
            {safePage} / {pages}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={safePage >= pages}
            onClick={() => set({ page: String(safePage + 1) })}
          >
            Next
          </Button>
        </div>
      ) : null}
    </>
  );
}
