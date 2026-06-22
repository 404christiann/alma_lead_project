import LoginForm from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(31,111,91,0.14),_transparent_38%),linear-gradient(180deg,_#fbfaf7_0%,_#f1ede4_100%)] px-4 py-12">
      <div className="w-full max-w-md animate-enter-up">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-900 text-lg font-semibold text-white shadow-lg shadow-emerald-950/20">
            A
          </div>
          <p className="text-sm font-medium text-emerald-700">Attorney portal</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-zinc-950">
            Attorney Login
          </h1>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            Sign in to access protected lead review tools.
          </p>
        </div>
        <div className="rounded-[1.5rem] border border-white/80 bg-white/90 p-3 shadow-2xl shadow-emerald-950/10 backdrop-blur">
          <div className="rounded-[1.1rem] border border-zinc-200/80 bg-white p-6 shadow-sm sm:p-8">
            <LoginForm />
          </div>
        </div>
        <p className="mt-5 text-center text-xs text-zinc-500">
          Access is restricted to authorized Alma attorneys.
        </p>
      </div>
    </main>
  );
}
