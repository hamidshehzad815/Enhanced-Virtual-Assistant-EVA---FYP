import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { CalendarProvider } from './contexts/CalendarContext';
import { SettingsProvider } from './contexts/SettingsContext';
import { ChatProvider } from './contexts/ChatContext';

import { AppShell } from './components/AppShell';
import { Welcome } from './pages/Welcome';
import { Features } from './pages/Features';
import { GetStarted } from './pages/GetStarted';
import { Auth } from './pages/Auth';
import { Home } from './pages/Home';
import { Chat } from './pages/Chat';
import { Calendar } from './pages/Calendar';
import { Roadmap } from './pages/Roadmap';
import { Collaboration } from './pages/Collaboration';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { VerifyEmail } from './pages/VerifyEmail';
import { ResetPassword } from './pages/ResetPassword';

import './App.css';

// Route protection wrapper for app shell views
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="global-loader-container">
        <div className="global-loader-spinner"></div>
        <span className="global-loader-text font-logo">Loading EVA...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/welcome" replace />;
  }

  return <AppShell>{children}</AppShell>;
};

// Route protection for public-only auth routes
const PublicRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="global-loader-container">
        <div className="global-loader-spinner"></div>
        <span className="global-loader-text font-logo">Loading EVA...</span>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
};

export const App = () => {
  return (
    <Router>
      <AuthProvider>
        <SettingsProvider>
          <CalendarProvider>
            <ChatProvider>
              <Routes>
                {/* Public / Pre-Auth Routes */}
                <Route path="/welcome" element={
                  <PublicRoute>
                    <Welcome />
                  </PublicRoute>
                } />
                <Route path="/features" element={
                  <PublicRoute>
                    <Features />
                  </PublicRoute>
                } />
                <Route path="/get-started" element={
                  <PublicRoute>
                    <GetStarted />
                  </PublicRoute>
                } />
                <Route path="/auth" element={
                  <PublicRoute>
                    <Auth />
                  </PublicRoute>
                } />
                <Route path="/verify-email" element={
                  <PublicRoute>
                    <VerifyEmail />
                  </PublicRoute>
                } />
                <Route path="/reset-password" element={
                  <PublicRoute>
                    <ResetPassword />
                  </PublicRoute>
                } />

                {/* Protected Dashboard & App Views */}
                <Route path="/" element={
                  <ProtectedRoute>
                    <Home />
                  </ProtectedRoute>
                } />
                <Route path="/chat" element={
                  <ProtectedRoute>
                    <Chat />
                  </ProtectedRoute>
                } />
                <Route path="/calendar" element={
                  <ProtectedRoute>
                    <Calendar />
                  </ProtectedRoute>
                } />
                <Route path="/roadmap" element={
                  <ProtectedRoute>
                    <Roadmap />
                  </ProtectedRoute>
                } />
                <Route path="/collaboration" element={
                  <ProtectedRoute>
                    <Collaboration />
                  </ProtectedRoute>
                } />
                <Route path="/analytics" element={
                  <ProtectedRoute>
                    <Analytics />
                  </ProtectedRoute>
                } />
                <Route path="/settings" element={
                  <ProtectedRoute>
                    <Settings />
                  </ProtectedRoute>
                } />

                {/* Catch-all Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ChatProvider>
          </CalendarProvider>
        </SettingsProvider>
      </AuthProvider>
    </Router>
  );
};

export default App;
