import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 28 28"
      width="22"
      height="22"
      aria-hidden
      className={cn("size-[22px]", className)}
    >
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
