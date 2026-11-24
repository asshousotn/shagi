import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";
import Skeleton from "../components/Skeleton";
import { useToast } from "../toast";

export default function AdminPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [tab, setTab] = useState("stats");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [reports, setReports] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [statsData, userData, reportData] = await Promise.all([
        api("/admin/stats"),
        api("/admin/users"),
        api("/admin/reports")
      ]);
      setStats(statsData);
      setUsers(userData);
      setReports(reportData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function changeRole(userId, role) {
    try {
      await api(`/admin/users/${userId}/role`, {
        method: "POST",
        body: JSON.stringify({ role })
      });
      showToast("Роль обновлена");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function resolveReport(id) {
    try {
      await api(`/admin/reports/${id}/resolve`, { method: "POST" });
      showToast("Жалоба закрыта");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <div className="section-head mb-24">
        <div>
          <h1>Администрирование</h1>
          <p className="muted">Вы: {user.name} · {user.role}</p>
        </div>
        <Icon name="bell" size={20} />
      </div>

      <div className="tags mb-24">
        {[["stats", "Сводка"], ["users", "Пользователи"], ["reports", "Жалобы"]].map(([key, label]) => (
          <button key={key} type="button" className={`tag ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>{label}</button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <Skeleton lines={5} />}

      {!loading && tab === "stats" && stats && (
        <div className="grid">
          {Object.entries(stats).map(([key, value]) => (
            <div className="card" key={key}>
              <div className="muted">{key.replace("_", " ")}</div>
              <h2>{value}</h2>
            </div>
          ))}
        </div>
      )}

      {!loading && tab === "users" && (
        <div className="chart-box">
          <table>
            <thead><tr><th>Имя</th><th>Email</th><th>Роль</th><th>Инструкций</th><th>Действие</th></tr></thead>
            <tbody>
              {users.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.email}</td>
                  <td>{item.role}</td>
                  <td>{item.instructions}</td>
                  <td>
                    {item.role === "owner" ? (
                      <span className="muted">владелец</span>
                    ) : user.role === "owner" ? (
                      <select
                        className="form-control w-auto"
                        value={item.role}
                        onChange={(event) => changeRole(item.id, event.target.value)}
                      >
                        <option value="student">ученик</option>
                        <option value="expert">эксперт</option>
                        <option value="admin">администратор</option>
                      </select>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && tab === "reports" && (
        <div className="chart-box">
          {reports.length === 0 && <p className="muted">Жалоб нет.</p>}
          {reports.map((item) => (
            <div className="card mb-12" key={item.id}>
              <div className="card-header">
                <div className="card-title">{item.target_type} #{item.target_id}</div>
                <span className="badge">{item.status}</span>
              </div>
              <p className="muted">{item.reason}</p>
              <p className="muted">От: {item.reporter} · {new Date(item.created_at).toLocaleString("ru-RU")}</p>
              {item.status === "open" && <button className="btn btn-outline" onClick={() => resolveReport(item.id)}>Закрыть</button>}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
