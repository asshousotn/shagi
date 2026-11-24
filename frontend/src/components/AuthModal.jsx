import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth";
import { useModalFocus } from "../useModalFocus";
import Icon from "./Icon";

export default function AuthModal() {
  const { authModal, closeAuth, openAuth, login, register } = useAuth();
  const mode = authModal;
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const modalRef = useRef(null);

  useEffect(() => {
    setName("");
    setEmail("");
    setPassword("");
    setError("");
  }, [mode]);

  useModalFocus(Boolean(mode), modalRef, closeAuth);

  if (!mode) return null;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await login(email, password);
      else await register(name, email, password);
      closeAuth();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const isLogin = mode === "login";

  return (
    <div
      className="modal-overlay active"
      onClick={(event) => {
        if (event.target === event.currentTarget) closeAuth();
      }}
    >
      <div className="modal" ref={modalRef}>
        <button type="button" className="modal-close" onClick={closeAuth} aria-label="Закрыть">
          <Icon name="close" size={20} />
        </button>
        <h2>{isLogin ? "Вход в систему" : "Регистрация"}</h2>
        <p>
          {isLogin
            ? "Войдите, чтобы сохранять прогресс и создавать инструкции."
            : "Создайте аккаунт, чтобы делиться инструкциями."}
        </p>
        <form onSubmit={submit}>
          {!isLogin && (
            <div className="form-group">
              <label>Имя</label>
              <input className="form-control" value={name} onChange={(event) => setName(event.target.value)} placeholder="Как к вам обращаться" required />
            </div>
          )}
          <div className="form-group">
            <label>Email</label>
            <input className="form-control" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="username" required />
          </div>
          <div className="form-group">
            <label>Пароль</label>
            <input className="form-control" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Не менее 4 символов" autoComplete={isLogin ? "current-password" : "new-password"} minLength={4} required />
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn btn-primary w-full" style={{ padding: 14, marginTop: 8 }} disabled={busy}>
            {busy ? "Подождите..." : isLogin ? "Войти" : "Создать аккаунт"}
          </button>
        </form>
        <div className="modal-switch">
          {isLogin ? "Нет аккаунта? " : "Уже есть аккаунт? "}
          <span onClick={() => openAuth(isLogin ? "register" : "login")}>
            {isLogin ? "Регистрация" : "Войти"}
          </span>
        </div>
      </div>
    </div>
  );
}
