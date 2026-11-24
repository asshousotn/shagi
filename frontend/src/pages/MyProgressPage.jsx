import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import ProgressBar from "../components/ProgressBar";
import Icon from "../components/Icon";

export default function MyProgressPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/me/progress")
      .then((data) => setItems(data.items))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <>
      <div className="section-head mb-24">
        <div>
          <h1>Мои прохождения</h1>
          <p className="muted">Продолжайте с того шага, на котором остановились.</p>
        </div>
        <Link to="/" className="btn btn-outline"><Icon name="left" size={16} /> В каталог</Link>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="chart-box">
        {items.length === 0 && <p className="muted">Вы ещё не начинали проходить инструкции.</p>}
        <ul className="grid">
          {items.map((item) => (
            <li key={item.instruction_id} className="card">
              <div className="card-header">
                <Link to={`/i/${item.instruction_id}/run`} className="card-title">{item.title}</Link>
                {item.finished && <span className="badge">Завершено</span>}
              </div>
              <ProgressBar value={item.percent} />
              <div className="card-meta">
                <span>{item.completed} из {item.total} шагов</span>
                <span>{item.percent}%</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
