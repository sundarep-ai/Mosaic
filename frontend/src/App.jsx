import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import ErrorBoundary from "./ErrorBoundary";
import Navbar from "./components/Navbar";
import Landing from "./pages/Landing";
import AddExpense from "./pages/AddExpense";
import AddIncome from "./pages/AddIncome";
import History from "./pages/History";
import Login from "./pages/Login";
import Settings from "./pages/Settings";

const Analytics = lazy(() => import("./pages/Analytics"));
const Calendar = lazy(() => import("./pages/Calendar"));
const Insights = lazy(() => import("./pages/Insights"));

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!user?.username) {
    return <Login />;
  }

  return (
    <div className="min-h-screen bg-background font-body text-on-surface">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-32 md:pb-8">
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/add" element={<AddExpense />} />
            <Route path="/edit/:id" element={<AddExpense />} />
            <Route path="/add-income" element={<AddIncome />} />
            <Route path="/analytics" element={
              <Suspense fallback={
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              }>
                <Analytics />
              </Suspense>
            } />
            <Route path="/calendar" element={
              <Suspense fallback={
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              }>
                <Calendar />
              </Suspense>
            } />
            <Route path="/insights" element={
              <Suspense fallback={
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              }>
                <Insights />
              </Suspense>
            } />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}
