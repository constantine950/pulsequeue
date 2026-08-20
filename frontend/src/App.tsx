import { useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import { Sidebar } from "./components/shared/Sidebar";
import { Navbar } from "./components/shared/Navbar";
import { getApiKey, setApiKey } from "./api/client";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import JobsPage from "./pages/JobsPage";
import WorkersPage from "./pages/WorkersPage";
import MetricsPage from "./pages/MetricsPage";
import FailedJobsPage from "./pages/FailedJobsPage";

function DashboardLayout({
  children,
  onLogout,
}: {
  children: React.ReactNode;
  onLogout: () => void;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar onLogout={onLogout} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}

function LoginWrapper({ onLogin }: { onLogin: (key: string) => void }) {
  const navigate = useNavigate();

  function handleLogin(key: string) {
    onLogin(key);
    navigate("/metrics");
  }

  return <LoginPage onLogin={handleLogin} />;
}

export default function App() {
  const [apiKey, setKey] = useState(getApiKey);

  function handleLogin(key: string) {
    setApiKey(key);
    setKey(key);
  }

  function handleLogout() {
    setApiKey("");
    setKey("");
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginWrapper onLogin={handleLogin} />} />

      <Route
        path="/metrics"
        element={
          <DashboardLayout onLogout={handleLogout}>
            <MetricsPage />
          </DashboardLayout>
        }
      />
      <Route
        path="/jobs"
        element={
          <DashboardLayout onLogout={handleLogout}>
            <JobsPage />
          </DashboardLayout>
        }
      />
      <Route
        path="/workers"
        element={
          <DashboardLayout onLogout={handleLogout}>
            <WorkersPage />
          </DashboardLayout>
        }
      />
      <Route
        path="/failed"
        element={
          <DashboardLayout onLogout={handleLogout}>
            <FailedJobsPage />
          </DashboardLayout>
        }
      />
    </Routes>
  );
}
