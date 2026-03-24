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
          <p className="text-sm text-on-surface-variant">
            {this.state.error.message}
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
