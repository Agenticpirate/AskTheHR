import { Link } from "react-router-dom";
import { PageEnter, Section } from "@/components/PageEnter";

export function Terms() {
  return (
    <PageEnter>
      <Section className="mb-12">
        <div className="micro text-primary">Legal</div>
        <h1 className="mt-3 text-5xl tracking-tight md:text-6xl">Terms.</h1>
        <p className="mt-4 max-w-xl text-sm text-muted-foreground">
          Short and current. Last updated 15 August 2026. 0pening is a product
          of AskTheHR.
        </p>
      </Section>

      <Section delay={0.06} className="prose-terms grid max-w-2xl gap-10 text-sm leading-relaxed">
        <article>
          <h2 className="text-2xl tracking-tight">What 0pening is</h2>
          <p className="mt-3 text-muted-foreground">
            0pening (digit zero) is a remote-first job dashboard with a private
            accountability loop. Browse openings, apply on the employer site,
            and log the work so the week stays honest. AskTheHR is the
            marketing brand behind it. We do not run a job board that takes
            applications on someone else&apos;s behalf.
          </p>
        </article>

        <article>
          <h2 className="text-2xl tracking-tight">Usernames</h2>
          <p className="mt-3 text-muted-foreground">
            You may claim one 0pening name. It must be 3–20 characters, start
            with a letter, and use only lowercase letters, numbers, and
            underscores. A username is a license to use that handle on 0pening.
            It is not your property. You do not buy it, sell it, or keep it
            against a valid complaint.
          </p>
          <p className="mt-3 text-muted-foreground">
            Some names are reserved: the 0pening and AskTheHR marks, common
            staff handles, major brands, and well-known public figures. Exact
            matches and simple lookalikes (extra underscores, or swapping{" "}
            <span className="font-mono">0</span>/<span className="font-mono">o</span>{" "}
            and <span className="font-mono">1</span>/<span className="font-mono">l</span>/
            <span className="font-mono">i</span>) are blocked. The reserved
            list is a starter set. We expand it on complaint. Impersonation is
            not allowed.
          </p>
        </article>

        <article>
          <h2 className="text-2xl tracking-tight">Trademark / complaint reclaim</h2>
          <p className="mt-3 text-muted-foreground">
            0pening may reclaim a username if a brand, trademark owner, or
            well-known person complains, or if the name impersonates them. If
            that happens, we will ask you to pick an alternate. We may hold or
            reassign the old name. We do not owe damages, payment, or a public
            explanation beyond that notice.
          </p>
        </article>

        <article>
          <h2 className="text-2xl tracking-tight">Job links</h2>
          <p className="mt-3 text-muted-foreground">
            Apply goes to the employer — their career site or applicant
            tracking system. We do not send you through third-party job boards
            or aggregators. Listings are a discovery slice. The employer owns
            the application.
          </p>
        </article>

        <article>
          <h2 className="text-2xl tracking-tight">Local data / no account yet</h2>
          <p className="mt-3 text-muted-foreground">
            There is no 0pening account today. Your tracker, nickname, optional
            email, and claimed name live in this browser. Clearing site data
            clears them. Optional email is stored locally only; we do not
            operate a mail list from this form. A public streak on the board
            is opt-in and shows only what you publish.
          </p>
        </article>

        <article>
          <h2 className="text-2xl tracking-tight">Contact</h2>
          <p className="mt-3 text-muted-foreground">
            Questions, trademark complaints, or reserved-name requests:{" "}
            <a
              href="mailto:support@0pening.com"
              className="text-primary underline-offset-4 hover:underline"
            >
              support@0pening.com
            </a>{" "}
            or AskTheHR. We will ask you to pick another name if yours has to
            come back.
          </p>
          <p className="mt-6">
            <Link to="/join" className="text-primary underline-offset-4 hover:underline">
              Claim a name
            </Link>
            <span className="text-muted-foreground"> · </span>
            <Link to="/" className="text-primary underline-offset-4 hover:underline">
              Home
            </Link>
          </p>
        </article>
      </Section>
    </PageEnter>
  );
}
