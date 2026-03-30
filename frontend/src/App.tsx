import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import LoginPage from './pages/LoginPage';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/AppLayout';
import ErrorBoundary from './components/ErrorBoundary';
import PositionsPage from './pages/PositionsPage';
import UploadPage from './pages/UploadPage';
import CandidatesPage from './pages/CandidatesPage';
import UsersPage from './pages/UsersPage';
import CandidateListPage from './pages/CandidateListPage';

const theme = {
  token: {
    colorPrimary: '#6366f1',
    borderRadius: 8,
    colorBgLayout: '#f8fafc',
  },
};

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <BrowserRouter>
        <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index element={<Navigate to="/positions" replace />} />
              <Route path="positions" element={<PositionsPage />} />
              <Route path="positions/:id/upload" element={<UploadPage />} />
              <Route path="positions/:id/candidates" element={<CandidatesPage />} />
              <Route path="candidates" element={<CandidateListPage />} />
              <Route path="users" element={<UsersPage />} />
            </Route>
          </Routes>
        </ErrorBoundary>
      </BrowserRouter>
    </ConfigProvider>
  );
}
