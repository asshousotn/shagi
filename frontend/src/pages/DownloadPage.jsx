import { Link } from "react-router-dom";
import Icon from "../components/Icon";

const CARDS = [
  {
    key: "android",
    title: "Android",
    meta: "APK · 688 КБ",
    href: "/downloads/taskills.apk",
    button: "Скачать APK",
    download: "taskills.apk",
    steps: [
      "Скачайте файл и откройте его.",
      "Разрешите установку из неизвестных источников.",
      "Нажмите «Установить».",
    ],
  },
  {
    key: "ios",
    title: "iPhone и iPad",
    meta: "Профиль · 29 КБ",
    href: "/downloads/taskills.mobileconfig",
    button: "Скачать профиль",
    download: null,
    steps: [
      "Откройте страницу в Safari и скачайте профиль.",
      "Настройки → Основные → VPN и управление устройством.",
      "Выберите «Taskills app» и нажмите «Установить».",
    ],
  },
];

function detectPlatform() {
  if (typeof navigator === "undefined") return "desktop";
  const ua = navigator.userAgent || "";
  if (/iPad|iPhone|iPod/.test(ua)) return "ios";
  if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) return "ios";
  if (/Android/i.test(ua)) return "android";
  return "desktop";
}

export default function DownloadPage() {
  const platform = detectPlatform();
  const cards = platform === "ios" ? [...CARDS].reverse() : CARDS;

  return (
    <>
      <section className="hero">
        <h1>Установить <span>Taskills</span></h1>
        <p>Иконка на рабочем столе — те же инструкции под рукой.</p>
      </section>

      <div className="download-grid">
        {cards.map((card) => (
          <div key={card.key} className={`download-card ${platform === card.key ? "is-current" : ""}`}>
            <div className="download-head">
              <span className={`download-badge ${card.key}`}>{card.title}</span>
              <span className="muted text-sm">{card.meta}</span>
            </div>

            <a
              className="btn btn-primary w-full"
              href={card.href}
              {...(card.download ? { download: card.download } : {})}
            >
              <Icon name="download" size={16} /> {card.button}
            </a>

            <ol className="download-steps">
              {card.steps.map((step, index) => <li key={index}>{step}</li>)}
            </ol>
          </div>
        ))}
      </div>

      <p className="download-footer">
        <Link to="/">Открыть в браузере</Link>
      </p>
    </>
  );
}
