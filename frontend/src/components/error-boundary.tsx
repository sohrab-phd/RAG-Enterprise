import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

type ErrorBoundaryProps = {
  readonly children: ReactNode;
};

type ErrorBoundaryState = {
  readonly hasError: boolean;
  readonly message: string;
};

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    message: "",
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      message: error.message || "An unexpected error occurred.",
    };
  }

  public componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Application error boundary", error, info.componentStack);
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false, message: "" });
  };

  public render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background p-6">
          <div
            role="alert"
            className="w-full max-w-lg space-y-4 rounded-lg border border-border bg-card p-6 shadow-sm"
          >
            <div className="space-y-1">
              <h1 className="text-xl font-semibold tracking-tight">Something went wrong</h1>
              <p className="text-sm text-muted-foreground">{this.state.message}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={this.handleRetry}>
                Try again
              </Button>
              <Button type="button" variant="outline" asChild>
                <Link to="/knowledge">Back to Knowledge</Link>
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
