import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function ExpertPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const data = await api("/expert/queue");
      setItems(data.items);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function verify(id) {
    try {
      await api(`/instructions/${id}/verify`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <h1>Очередь эксперта</h1>
      {error && <p className="error">{error}</p>}
      {items.length === 0 && <p>Непроверенных инструкций нет.</p>}
      <ul className="grid">
        {items.map((item) => (
          <li key={item.id} className="card">
            <Link to={`/i/${item.id}`}><b>{item.title}</b></Link> · {item.author.name} ·{" "}
            ★ {item.rating_avg} ({item.rating_count}) · {item.steps_count} шагов{" "}
            <button type="button" className="btn btn-primary" onClick={() => verify(item.id)}>Проверить</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
