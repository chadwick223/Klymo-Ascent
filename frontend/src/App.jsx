import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
import Home from './pages/Home';
import ProfileSetup from './pages/ProfileSetup';
import Verification from './pages/Verification';
import MatchQueue from './pages/MatchQueue';
import Chat from './pages/Chat';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/home" element={<Home />} />
        <Route path="/setup-profile" element={<ProfileSetup />} />
        <Route path="/verify" element={<Verification />} />
        <Route path="/queue" element={<MatchQueue />} />
        <Route path="/chat/:chatId" element={<Chat />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
