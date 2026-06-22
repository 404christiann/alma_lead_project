import IntakeForm from "@/components/IntakeForm";

export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(31,111,91,0.14),_transparent_34%),linear-gradient(135deg,_#fbfaf7_0%,_#f3efe6_100%)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center gap-10 lg:grid-cols-[1fr_480px]">
        <section className="order-2 max-w-2xl animate-enter-up lg:order-1">
          <h1 className="text-balance text-4xl font-semibold tracking-[-0.03em] text-zinc-950 sm:text-5xl">
            Share your details with Alma&apos;s legal team.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-zinc-600">
            Submit your contact information and resume so an attorney can review
            your lead and follow up with the right next step.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              ["Private upload", "Files are stored in local object storage."],
              ["Fast review", "Attorneys see new leads immediately."],
              ["Clear status", "Every lead starts pending review."],
            ].map(([title, copy]) => (
              <div
                key={title}
                className="rounded-xl border border-white/80 bg-white/60 p-4 shadow-sm backdrop-blur"
              >
                <p className="text-sm font-semibold text-zinc-900">{title}</p>
                <p className="mt-1 text-xs leading-5 text-zinc-500">{copy}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="order-1 animate-enter-up lg:order-2">
          <div className="rounded-[1.75rem] border border-white/80 bg-white/85 p-3 shadow-2xl shadow-emerald-950/10 backdrop-blur">
            <div className="rounded-[1.35rem] border border-zinc-200/80 bg-white p-6 shadow-sm sm:p-8">
              <div className="mb-7">
                <p className="text-sm font-medium text-emerald-700">
                  Prospect intake
                </p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-zinc-950">
                  Apply Now
                </h2>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  Fill in your details below and upload your resume.
                </p>
              </div>
              <IntakeForm />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
