import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useRef } from "react";

/** Fade table rows in. Opacity works on `<tr>`; transform does not. */
export function useTableEnter(depKey: string, reduce: boolean | null) {
  const ref = useRef<HTMLTableSectionElement>(null);

  useGSAP(
    () => {
      const rows = ref.current?.querySelectorAll("tr");
      if (!rows?.length) return;
      if (reduce) {
        gsap.set(rows, { opacity: 1 });
        return;
      }
      gsap.fromTo(
        rows,
        { opacity: 0 },
        {
          opacity: 1,
          duration: 0.2,
          stagger: 0.022,
          ease: "power2.out",
          overwrite: true,
        },
      );
    },
    { dependencies: [depKey, reduce] },
  );

  return ref;
}
