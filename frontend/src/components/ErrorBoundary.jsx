import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="chart-box">
        <h2>Что-то пошло не так</h2>
        <p className="muted">{this.state.error.message}</p>
        <button className="btn btn-primary mt-16" onClick={() => window.location.reload()}>
          Перезагрузить страницу
        </button>
      </div>
    );
  }
}
