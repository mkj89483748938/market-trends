export default function LoginPage({
  searchParams,
}: {
  searchParams: { next?: string; error?: string };
}) {
  const next = searchParams.next ?? "/";
  const hasError = searchParams.error === "1";

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form
        action="/api/login"
        method="POST"
        className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-700 dark:bg-slate-800"
      >
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">OC Market Trends</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Enter the team password to continue.</p>

        <input type="hidden" name="next" value={next} />

        <label className="mt-6 block text-sm font-medium text-slate-700 dark:text-slate-300" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          required
          autoFocus
          className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100"
        />

        {hasError && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">Incorrect password. Try again.</p>
        )}

        <button
          type="submit"
          className="mt-4 w-full rounded-md bg-brand-500 px-3 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          Sign in
        </button>
      </form>
    </main>
  );
}
