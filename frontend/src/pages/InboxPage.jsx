import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function InboxPage() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const data = await api("/me/inbox");
      setItems(data.items);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function resolve(id) {
    try {
      await api(`/comments/${id}/resolve`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <h1>Входящие предложения</h1>
      {error && <p className="error">{error}</p>}
      {items.length === 0 && <p>Новых предложений нет.</p>}
      <ul className="grid">
        {items.map((item) => (
          <li key={item.id} className="card">
            <div>
              <Link to={`/i/${item.instruction_id}`}><b>{item.instruction_title}</b></Link>
              {item.step_title && <> · шаг «{item.step_title}»</>}
            </div>
            <div>{item.body}</div>
            <small className="muted">{item.user} · {new Date(item.created_at).toLocaleString("ru-RU")}</small>
            <div><button type="button" className="btn btn-primary" onClick={() => resolve(item.id)}>Решено</button></div>
          </li>
        ))}
      </ul>
    </div>
  );
}
