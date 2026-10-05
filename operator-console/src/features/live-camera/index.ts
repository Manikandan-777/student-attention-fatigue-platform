import React, { Component, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
}

export class LiveCameraErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('LiveCamera feature error:', error, info);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return null; // Gracefully contain crash without taking down surrounding UI
    }
    return this.props.children;
  }
}

