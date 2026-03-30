import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 48, textAlign: 'center' }}>
          <h2 style={{ color: '#ef4444' }}>页面出错了</h2>
          <p style={{ color: '#71717a' }}>请刷新页面重试</p>
          <a href="/" style={{ color: '#6366f1' }}>返回首页</a>
        </div>
      );
    }
    return this.props.children;
  }
}
