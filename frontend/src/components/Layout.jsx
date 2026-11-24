import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { api, assetUrl } from "../api";
import { useAuth } from "../auth";
import Icon from "./Icon";
import AuthModal from "./AuthModal";

export default function Layout() {
  const { user, logout, openAuth } = useAuth();
  const location = useLocation();
  const [notifications, setNotifications] = useState([]);
  const [notifOpen, setNotifOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    api("/me/notifications").then(setNotifications).catch(() => {});
  }, [user?.id]);

  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  const unread = notifications.filter((item) => !item.read_at).length;

  async function readNotification(id) {
    try {
      const updated = await api(`/me/notifications/${id}/read`, { method: "POST" });
      setNotifications((current) => current.map((item) => (item.id === id ? updated : item)));
    } catch {
      setNotifications((current) => current);
    }
  }
  const active = (path) => path === "/" ? location.pathname === "/" || location.pathname.startsWith("/i") : location.pathname.startsWith(path);

  function exit() {
    logout();
    window.location.href = "/";
  }

  return (
    <>
      <header>
        <div className="header-container">
          <Link to="/" className="logo">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            Taskills
          </Link>

          <nav className="main-nav">
            <Link to="/">Каталог</Link>
            <Link to="/forum">Форум</Link>
            <Link to="/leaderboard">Топ</Link>
            <Link to="/download">Скачать</Link>
            {user && <Link to="/dashboard">Мои инструкции</Link>}
            {user && <Link to="/dashboard/1/analytics">Аналитика</Link>}
            {user && <Link to="/progress">Прохождения</Link>}
            {user && <Link to="/inbox">Предложения</Link>}
            {user?.role === "expert" && <Link to="/expert">Эксперт</Link>}
            {(user?.role === "admin" || user?.role === "owner") && <Link to="/admin">Админ</Link>}
          </nav>

          {user ? (
            <div className="user-profile">
              <button type="button" className="btn btn-outline" onClick={() => setNotifOpen(true)} aria-label="Уведомления">
                <Icon name="bell" size={18} />
                {unread > 0 && <span className="badge">{unread}</span>}
              </button>
              <Link to={`/u/${user.id}`} className="muted" style={{ fontSize: 14, fontWeight: 600 }}>
                {user.name}
              </Link>
              {user.avatar_url ? (
                <img src={assetUrl(user.avatar_url)} alt="" className="avatar" style={{ objectFit: "cover" }} />
              ) : (
                <div className="avatar">{user.name[0]}</div>
              )}
              <button type="button" className="btn btn-outline" onClick={exit}>Выйти</button>
            </div>
          ) : (
            <div className="auth-buttons">
              <button type="button" className="btn btn-outline" onClick={() => openAuth("login")}>Войти</button>
              <button type="button" className="btn btn-primary" onClick={() => openAuth("register")}>Регистрация</button>
            </div>
          )}

          <Link to="/download" className="btn btn-outline">
            <Icon name="download" size={16} /> Скачать
          </Link>

          <button
            type="button"
            className="menu-button"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Меню"
          >
            <Icon name="menu" size={22} />
          </button>
        </div>

        {menuOpen && (
          <nav className="mobile-nav">
            <Link to="/">Каталог</Link>
            <Link to="/forum">Форум</Link>
            <Link to="/leaderboard">Топ</Link>
            <Link to="/download">Скачать приложение</Link>
            {user && <Link to="/dashboard">Мои инструкции</Link>}
            {user && <Link to="/dashboard/1/analytics">Аналитика</Link>}
            {user && <Link to="/progress">Прохождения</Link>}
            {user && <Link to="/inbox">Предложения</Link>}
            {user?.role === "expert" && <Link to="/expert">Эксперт</Link>}
            {(user?.role === "admin" || user?.role === "owner") && <Link to="/admin">Админ</Link>}
            {user ? (
              <>
                <Link to={`/u/${user.id}`}>Профиль</Link>
                <button type="button" onClick={() => setNotifOpen(true)}>Уведомления{unread > 0 ? ` (${unread})` : ""}</button>
                <button type="button" onClick={exit}>Выйти</button>
              </>
            ) : (
              <>
                <button type="button" onClick={() => openAuth("login")}>Войти</button>
                <button type="button" onClick={() => openAuth("register")}>Регистрация</button>
              </>
            )}
          </nav>
        )}
      </header>
      <main><Outlet /></main>

      <nav className="bottom-nav">
        <Link to="/" className={active("/") ? "active" : ""}>
          <Icon name="home" size={20} /><span>Каталог</span>
        </Link>
        {user ? (
          <Link to="/dashboard" className={active("/dashboard") ? "active" : ""}>
            <Icon name="list" size={20} /><span>Мои</span>
          </Link>
        ) : (
          <button type="button" onClick={() => openAuth("login")}>
            <Icon name="list" size={20} /><span>Войти</span>
          </button>
        )}
        {user ? (
          <Link to="/dashboard/new" className={active("/dashboard/new") ? "active" : ""}>
            <Icon name="plus" size={20} /><span>Создать</span>
          </Link>
        ) : (
          <button type="button" onClick={() => openAuth("register")}>
            <Icon name="plus" size={20} /><span>Регистрация</span>
          </button>
        )}
        <Link to={user ? `/u/${user.id}` : "/leaderboard"} className={active(user ? "/u" : "/leaderboard") ? "active" : ""}>
          <Icon name={user ? "user" : "trophy"} size={20} /><span>{user ? "Профиль" : "Топ"}</span>
        </Link>
      </nav>

      {notifOpen && (
        <div className="modal-overlay active" onClick={(event) => { if (event.target === event.currentTarget) setNotifOpen(false); }}>
          <div className="modal">
            <button type="button" className="modal-close" onClick={() => setNotifOpen(false)} aria-label="Закрыть">
              <Icon name="close" size={20} />
            </button>
            <h2>Уведомления</h2>
            {notifications.length === 0 && <p className="muted">Пока нет уведомлений.</p>}
            <div className="comment-list mt-16">
              {notifications.map((item) => (
                <div className="comment-item" key={item.id}>
                  <div className="comment-avatar"><Icon name="bell" size={14} /></div>
                  <div className="comment-body">
                    <div className="comment-author">
                      {item.type === "suggestion_accepted" && "Предложение принято"}
                      {item.type === "fork_created" && "Создан форк"}
                      {item.type === "verified" && "Инструкция проверена"}
                      {item.type === "forum_reply" && "Ответ на форуме"}
                      {item.type === "forum_quote" && "Ответ на ваше сообщение"}
                      {item.type === "solution_marked" && "Ваш ответ — решение"}
                      {!["suggestion_accepted", "fork_created", "verified", "forum_reply", "forum_quote", "solution_marked"].includes(item.type) && item.type}
                    </div>
                    <div>{item.payload.instruction_title}</div>
                    {item.payload.user && <div className="muted">{item.payload.user}</div>}
                    {item.payload.expert && <div className="muted">{item.payload.expert}</div>}
                    <div className="muted">{new Date(item.created_at).toLocaleString("ru-RU")}</div>
                    {!item.read_at && (
                      <button className="btn btn-outline mt-8" onClick={() => readNotification(item.id)}>Прочитано</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <AuthModal />
    </>
  );
}
