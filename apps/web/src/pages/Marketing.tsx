import { PageEnter } from "@/components/PageEnter";
import { AeoAnswer } from "@/components/marketing/AeoAnswer";
import { Faq } from "@/components/marketing/Faq";
import { FinalCta } from "@/components/marketing/FinalCta";
import { HowCadenceWorks } from "@/components/marketing/HowCadenceWorks";
import { JobBoardExplain } from "@/components/marketing/JobBoardExplain";
import { MarketingHero } from "@/components/marketing/MarketingHero";
import { Pricing } from "@/components/marketing/Pricing";
import { ProductBento } from "@/components/marketing/ProductBento";

export function Marketing() {
  return (
    <PageEnter className="mx-auto w-full max-w-[1120px] px-5 py-10 md:px-12 md:py-16">
      <MarketingHero />
      <AeoAnswer />
      <div className="mt-20 flex flex-col gap-20 md:mt-28 md:gap-28">
        <HowCadenceWorks />
        <ProductBento />
        <JobBoardExplain />
        <Pricing />
        <Faq />
        <FinalCta />
      </div>
    </PageEnter>
  );
}
