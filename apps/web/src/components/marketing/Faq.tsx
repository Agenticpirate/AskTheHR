import { ChevronDown } from "lucide-react";
import { Section } from "@/components/PageEnter";
import { FAQS } from "@/data/marketing";

export function Faq() {
  return (
    <Section id="faq" delay={0.18} className="marketing-defer scroll-mt-20">
      <div className="micro text-primary">FAQ</div>
      <h2 className="mt-2 max-w-xl text-3xl tracking-tight md:text-5xl">
        Straight answers.
      </h2>
      <div className="mt-10 flex flex-col border-t border-border">
        {FAQS.map((item, i) => (
          <details
            key={item.id}
            id={item.id}
            name="faq"
            className="group border-b border-border"
            open={i === 0}
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-left text-base tracking-tight md:text-lg [&::-webkit-details-marker]:hidden">
              {item.question}
              <ChevronDown
                aria-hidden
                className="shrink-0 text-muted-foreground transition-transform group-open:rotate-180"
              />
            </summary>
            <p className="pb-5 text-sm leading-relaxed text-muted-foreground md:text-base">
              {item.answer}
            </p>
          </details>
        ))}
      </div>
    </Section>
  );
}
