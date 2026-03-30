import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-error">
          <p className="font-bold mb-2">Something went wrong.</p>
          <p className="text-sm text-on-surface-variant mb-4">
            {this.state.error.message}
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            className="px-4 py-2 rounded-full bg-primary text-on-primary font-bold text-sm hover:shadow-lg transition-all"
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
