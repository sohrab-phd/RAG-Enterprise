import { Button } from "@/components/ui/button";

function App() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="max-w-lg space-y-3 text-center">
        <p className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
          RAG-enterprise
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Frontend skeleton ready
        </h1>
        <p className="text-muted-foreground">
          React, Vite, TypeScript, Tailwind CSS, and shadcn/ui are configured.
          Business features will be implemented in future iterations.
        </p>
      </div>
      <Button type="button">Placeholder action</Button>
    </main>
  );
}

export default App;
