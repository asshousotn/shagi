import { createContext, useContext, useState } from "react";
import Icon from "./components/Icon";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [confirmData, setConfirmData] = useState(null);

  function showToast(message, type = "info") {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message, type }]);
    setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 3500);
  }

  function ask(message) {
    return new Promise((resolve) => setConfirmData({ message, resolve }));
  }

  function answer(value) {
    if (confirmData) confirmData.resolve(value);
    setConfirmData(null);
  }

  return (
    <ToastContext.Provider value={{ showToast, ask }}>
      {children}
      <div className="toast-stack">
        {toasts.map((item) => (
          <div key={item.id} className={`toast ${item.type}`}>
            <Icon name={item.type === "error" ? "warning" : "check"} size={16} />
            <span>{item.message}</span>
          </div>
        ))}
      </div>
      {confirmData && (
        <div className="modal-overlay active" onClick={(event) => { if (event.target === event.currentTarget) answer(false); }}>
          <div className="modal">
            <h2>Подтверждение</h2>
            <p>{confirmData.message}</p>
            <div className="row gap-12">
              <button className="btn btn-primary" onClick={() => answer(true)}>Да</button>
              <button className="btn btn-outline" onClick={() => answer(false)}>Отмена</button>
            </div>
          </div>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
