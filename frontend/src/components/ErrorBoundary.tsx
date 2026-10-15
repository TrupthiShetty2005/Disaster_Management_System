import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<{ children: ReactNode; resetKey: string }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidUpdate(prev: { resetKey: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300" role="alert">
          This page failed to render: {this.state.error.message}
        </div>
      );
    }
    return this.props.children;
  }
}
