import { useEffect, useState } from "react";
import Skeleton from "../components/Skeleton";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function LeaderboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/leaderboard")
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <Skeleton />;

  return (
    <div>
      <h1>Топ</h1>
      <h2 className="mb-16">Инструкции</h2>
      <div className="chart-box mb-24">
      <table>
        <thead>
          <tr><th>#</th><th>Название</th><th>Автор</th><th>Рейтинг</th><th>Просмотры</th><th>Score</th></tr>
        </thead>
        <tbody>
          {data.instructions.map((item, index) => (
            <tr key={item.id}>
              <td>{index + 1}</td>
              <td><Link to={`/i/${item.id}`}>{item.title}</Link></td>
              <td>{item.author.name}</td>
              <td>★ {item.rating_avg} ({item.rating_count})</td>
              <td>{item.views}</td>
              <td>{item.score}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>

      <h2 className="mb-16">Авторы</h2>
      <div className="chart-box">
      <table>
        <thead>
          <tr><th>#</th><th>Имя</th><th>Роль</th><th>Инструкций</th><th>Просмотры</th><th>Рейтинг</th></tr>
        </thead>
        <tbody>
          {data.authors.map((author, index) => (
            <tr key={author.id}>
              <td>{index + 1}</td>
              <td><Link to={`/u/${author.id}`}>{author.name}</Link></td>
              <td>{author.role === "expert" ? "эксперт" : "ученик"}</td>
              <td>{author.instructions}</td>
              <td>{author.views}</td>
              <td>★ {author.rating_avg}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}
