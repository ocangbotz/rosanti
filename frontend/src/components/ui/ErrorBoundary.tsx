import { AlertTriangle } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Last-resort catch for render-time crashes (e.g. an unexpected API
 * response shape). Without this, any uncaught error in a page component
 * unmounts the whole React tree to a blank white screen with nothing but
 * a console trace — this renders a recoverable, on-brand fallback instead.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled error in component tree:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface-page px-6 text-center">
          <AlertTriangle className="text-status-critical" size={36} />
          <div className="space-y-1">
            <h1 className="text-lg font-semibold text-ink-primary">Something went wrong</h1>
            <p className="max-w-md text-sm text-ink-secondary">
              The app hit an unexpected error and couldn't continue rendering this page. Reloading
              usually fixes it; if it keeps happening, check the browser console for details.
            </p>
          </div>
          <Button variant="primary" size="md" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
