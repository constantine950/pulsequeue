import { Routes, Route } from "react-router-dom";
import { Sidebar } from "./components/shared/Sidebar";
import { Navbar } from "./components/shared/Navbar";
import LandingPage from "./pages/LandingPage";
import JobsPage from "./pages/JobsPage";
import WorkersPage from "./pages/WorkersPage";
import MetricsPage from "./pages/MetricsPage";
import FailedJobsPage from "./pages/FailedJobsPage";

function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      {/* Landing — no sidebar */}
      <Route path="/" element={<LandingPage />} />

      {/* Dashboard routes — with sidebar */}
      <Route
        path="/metrics"
        element={
          <DashboardLayout>
            <MetricsPage />
          </DashboardLayout>
        }
      />
      <Route
        path="/jobs"
        element={
          <DashboardLayout>
            <JobsPage />
          </DashboardLayout>
        }
      />
      <Route
        path="/workers"
        element={
          <DashboardLayout>
            <WorkersPage />
          </DashboardLayout>
        }
      />
      <Route
        path="/failed"
        element={
          <DashboardLayout>
            <FailedJobsPage />
          </DashboardLayout>
        }
      />
    </Routes>
  );
}
