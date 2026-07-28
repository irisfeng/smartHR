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
import ForceChangePasswordPage from './pages/ForceChangePasswordPage';

const theme = {
  token: {
    colorPrimary: '#2563eb',
    colorInfo: '#2563eb',
    colorSuccess: '#16a34a',
    colorWarning: '#d97706',
    colorError: '#dc2626',
    colorText: '#111827',
    colorTextSecondary: '#475569',
    colorBorder: '#e5e7eb',
    borderRadius: 8,
    colorBgLayout: '#f5f7fb',
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  components: {
    Button: {
      controlHeight: 36,
      borderRadius: 8,
    },
    Card: {
      borderRadiusLG: 10,
    },
    Table: {
      headerBg: '#f8fafc',
      rowHoverBg: '#f8fafc',
    },
    Input: {
      borderRadius: 8,
    },
    Select: {
      borderRadius: 8,
    },
  },
};

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <BrowserRouter>
        <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/force-change-password" element={<ForceChangePasswordPage />} />
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
