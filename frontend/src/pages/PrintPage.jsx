import { useEffect, useState } from "react";
import Skeleton from "../components/Skeleton";
import { Link, useParams } from "react-router-dom";
import { api, assetUrl } from "../api";

export default function PrintPage() {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/instructions/${id}`)
      .then(setItem)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) return <p className="error">{error}</p>;
  if (!item) return <Skeleton />;

  return (
    <div>
      <p className="no-print">
        <Link to={`/i/${id}`}>← Назад</Link>{" "}
        <button type="button" className="btn btn-primary no-print" onClick={() => window.print()}>Печать / сохранить PDF</button>
      </p>
      <h1>{item.title}</h1>
      <p>
        Автор: {item.author.name} · {item.category?.name || "Без категории"} ·{" "}
        {item.minutes} мин · ★ {item.rating_avg} ({item.rating_count})
      </p>
      <p>{item.summary}</p>
      <ol>
        {item.steps.map((step) => (
          <li key={step.id} className="mb-12">
            <b>{step.title}</b>
            <div>{step.body}</div>
            {step.image_url && <div><img src={assetUrl(step.image_url)} alt="" style={{ maxWidth: 320 }} /></div>}
            {step.images.map((image) => <div key={image.id}><img src={assetUrl(image.url)} alt="" style={{ maxWidth: 320, marginTop: 8 }} /></div>)}
          </li>
        ))}
      </ol>
      <p className="muted">Источник: {window.location.origin}/i/{item.id}</p>
    </div>
  );
}
