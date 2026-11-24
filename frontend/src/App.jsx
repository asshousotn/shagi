import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { ToastProvider } from "./toast";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import AdminPage from "./pages/AdminPage";
import ForumPage from "./pages/ForumPage";
import ForumTopicPage from "./pages/ForumTopicPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import BookmarksPage from "./pages/BookmarksPage";
import CatalogPage from "./pages/CatalogPage";
import DashboardPage from "./pages/DashboardPage";
import DownloadPage from "./pages/DownloadPage";
import EditorPage from "./pages/EditorPage";
import ExpertPage from "./pages/ExpertPage";
import InboxPage from "./pages/InboxPage";
import InstructionPage from "./pages/InstructionPage";
import LeaderboardPage from "./pages/LeaderboardPage";
import LoginPage from "./pages/LoginPage";
import MyProgressPage from "./pages/MyProgressPage";
import NotFoundPage from "./pages/NotFoundPage";
import PrintPage from "./pages/PrintPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import RunPage from "./pages/RunPage";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p>Загрузка...</p>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function RequireAdmin({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <p>Загрузка...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!["admin", "owner"].includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <ErrorBoundary>
          <AuthProvider>
            <Routes>
          <Route element={<Layout />}>
            <Route index element={<CatalogPage />} />
            <Route path="i/:id" element={<InstructionPage />} />
            <Route path="i/:id/run" element={<RunPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="leaderboard" element={<LeaderboardPage />} />
            <Route path="download" element={<DownloadPage />} />
            <Route path="forum" element={<ForumPage />} />
            <Route path="forum/:id" element={<ForumTopicPage />} />
            <Route path="admin" element={<RequireAdmin><AdminPage /></RequireAdmin>} />
            <Route path="u/:id" element={<ProfilePage />} />
            <Route path="dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
            <Route path="dashboard/new" element={<RequireAuth><EditorPage /></RequireAuth>} />
            <Route path="dashboard/:id/edit" element={<RequireAuth><EditorPage /></RequireAuth>} />
            <Route path="dashboard/:id/analytics" element={<RequireAuth><AnalyticsPage /></RequireAuth>} />
            <Route path="progress" element={<RequireAuth><MyProgressPage /></RequireAuth>} />
            <Route path="bookmarks" element={<RequireAuth><BookmarksPage /></RequireAuth>} />
            <Route path="inbox" element={<RequireAuth><InboxPage /></RequireAuth>} />
            <Route path="expert" element={<RequireAuth><ExpertPage /></RequireAuth>} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
          <Route path="embed/:id" element={<RunPage embedded />} />
          <Route path="i/:id/print" element={<PrintPage />} />
            </Routes>
          </AuthProvider>
        </ErrorBoundary>
      </ToastProvider>
    </BrowserRouter>
  );
}
