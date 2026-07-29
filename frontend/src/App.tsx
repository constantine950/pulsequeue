import { useState } from "react";
import { Routes, Route } from "react-router-dom";
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

  // If API key is configured in backend but not set in frontend, show login
  // We detect this by checking if we stored a key or if we're on /login
  const needsLogin = window.location.pathname === "/login";

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />

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
