import { Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/shared/Sidebar";
import { Navbar } from "./components/shared/Navbar";
import JobsPage from "./pages/JobsPage";
import WorkersPage from "./pages/WorkersPage";
import MetricsPage from "./pages/MetricsPage";
import FailedJobsPage from "./pages/FailedJobsPage";

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-auto p-6">
          <Routes>
            <Route path="/" element={<Navigate to="/metrics" replace />} />
            <Route path="/metrics" element={<MetricsPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/workers" element={<WorkersPage />} />
            <Route path="/failed" element={<FailedJobsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
