import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div>
      <h1>404</h1>
      <p>Такой страницы нет.</p>
      <p><Link to="/" className="btn btn-primary">В каталог</Link></p>
    </div>
  );
}
