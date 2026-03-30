import { useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  FileTextOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import api from '../api';

const { Sider, Content, Header } = Layout;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, setUser, logout } = useAuthStore();

  useEffect(() => {
    if (!user) {
      api.get('/api/auth/me').then((res) => setUser(res.data)).catch(() => {
        logout();
        navigate('/login');
      });
    }
  }, []);

  const selectedKey = '/' + location.pathname.split('/')[1];

  const menuItems = [
    { key: '/positions', icon: <FileTextOutlined />, label: '职位管理' },
    ...(user?.role === 'manager' ? [] : [{ key: '/candidates', icon: <TeamOutlined />, label: '候选人管理' }]),
    { key: '/users', icon: <SettingOutlined />, label: '用户管理' },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={210}
        style={{
          background: '#fff',
          borderRight: '1px solid #f0f0f5',
        }}
      >
        <div style={{
          padding: '20px 24px',
          fontSize: 20,
          fontWeight: 600,
          color: '#6366f1',
          letterSpacing: 1,
        }}>
          SmartHR
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ border: 'none' }}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f5',
          height: 56,
        }}>
          <span style={{ color: '#71717a', fontSize: 13 }}>
            {user?.display_name}
            <a onClick={() => { logout(); navigate('/login'); }} style={{ marginLeft: 12, color: '#6366f1' }}>退出</a>
          </span>
        </Header>
        <Content style={{ padding: 28, background: '#f8fafc' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
