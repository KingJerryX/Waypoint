import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import GoPage from "./pages/GoPage";
import HowItWorks from "./pages/HowItWorks";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/go/:slug" element={<GoPage />} />
      <Route path="/how-it-works" element={<HowItWorks />} />
    </Routes>
  );
}
