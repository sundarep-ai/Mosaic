import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Landing from "./pages/Landing";
import AddExpense from "./pages/AddExpense";
import Analytics from "./pages/Analytics";
import History from "./pages/History";

export default function App() {
  return (
    <div className="min-h-screen bg-background font-body text-on-surface">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-32 md:pb-8">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/add" element={<AddExpense />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </div>
  );
}
