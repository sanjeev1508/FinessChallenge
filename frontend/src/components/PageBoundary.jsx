import { Component } from "react";
import { ErrorBox } from "./Status.jsx";

export default class PageBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    console.error("Page failed to load or render", error, info);
  }

  render() {
    if (this.state.failed) {
      return <ErrorBox error={{ message: "This page could not load. Reload to try again." }}
        onRetry={() => location.reload()} />;
    }
    return this.props.children;
  }
}
