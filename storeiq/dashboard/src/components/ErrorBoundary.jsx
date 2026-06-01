import React from "react";

/**
 * Error boundary to catch rendering errors in child components
 * without crashing the entire application.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("StoreIQ ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-center">
          <div className="text-lg font-display text-red-400">Component Error</div>
          <p className="text-sm text-white/60 mt-2">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-4 px-4 py-2 bg-white/10 rounded-xl text-sm hover:bg-white/20 transition"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
