import { useEffect, useState } from "react";
import { initials } from "@/lib/format";
import { fallbackLogoUrl, logoDomain, logoUrl } from "@/lib/logo";
import { cn } from "@/lib/utils";

type Size = 20 | 24 | 28;

export function CompanyLogo({
  url,
  company,
  size = 20,
  className,
}: {
  url: string;
  company: string;
  size?: Size;
  className?: string;
}) {
  const domain = logoDomain(url, company);
  const primary = domain ? logoUrl(domain) : "";
  const fallback = domain ? fallbackLogoUrl(domain) : "";
  const [phase, setPhase] = useState<"primary" | "fallback" | "initials">(
    domain ? "primary" : "initials",
  );

  useEffect(() => {
    setPhase(domain ? "primary" : "initials");
  }, [domain]);

  const box =
    size === 28 ? "size-7 text-[11px]" : size === 24 ? "size-6 text-[10px]" : "size-5 text-[9px]";

  if (phase === "initials" || !domain) {
    return (
      <span
        aria-hidden
        className={cn(
          "grid shrink-0 place-items-center rounded-sm bg-primary/10 font-medium text-primary",
          box,
          className,
        )}
      >
        {initials(company)}
      </span>
    );
  }

  const src = phase === "primary" ? primary : fallback;

  return (
    <img
      src={src}
      alt=""
      width={size}
      height={size}
      decoding="async"
      referrerPolicy="no-referrer"
      className={cn("shrink-0 rounded-sm bg-white object-contain", box, className)}
      onError={() => {
        setPhase((current) => (current === "primary" ? "fallback" : "initials"));
      }}
    />
  );
}
