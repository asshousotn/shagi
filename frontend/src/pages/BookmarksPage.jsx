import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function BookmarksPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/me/bookmarks")
      .then((data) => setItems(data.items))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <h1>Избранное</h1>
      {error && <p className="error">{error}</p>}
      {items.length === 0 && <p>Пока пусто.</p>}
      <ul className="grid">
        {items.map((item) => (
          <li key={item.id} className="card">
            <Link to={`/i/${item.id}`}><b>{item.title}</b></Link>
            <div>{item.summary}</div>
            <small className="muted">★ {item.rating_avg} · {item.steps_count} шагов · {item.author.name}</small>
          </li>
        ))}
      </ul>
    </div>
  );
}
