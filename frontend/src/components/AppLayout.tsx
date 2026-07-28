import { useEffect, useState, type ReactNode } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Avatar, Button, Drawer, Dropdown, Form, Grid, Input, Layout, Menu, Modal, message } from 'antd';
import {
  FileTextOutlined,
  LockOutlined,
  LogoutOutlined,
  MenuOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import api from '../api';

const { Sider, Content, Header } = Layout;
const { useBreakpoint } = Grid;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, setUser, logout } = useAuthStore();
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (!user) {
      api.get('/api/auth/me').then((res) => setUser(res.data)).catch(() => {
        logout();
        navigate('/login');
      });
    }
  }, []);

  const [pwdOpen, setPwdOpen] = useState(false);
  const [pwdForm] = Form.useForm();
  const [pwdLoading, setPwdLoading] = useState(false);

  const handleChangePassword = async () => {
    const values = await pwdForm.validateFields();
    if (values.new_password !== values.confirm_password) {
      message.error('两次密码不一致');
      return;
    }
    setPwdLoading(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      message.success('密码修改成功');
      setPwdOpen(false);
      pwdForm.resetFields();
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      if (Array.isArray(detail)) {
        message.error(detail.map((d: any) => d.msg).join('; '));
      } else {
        message.error(detail || '修改失败');
      }
    } finally {
      setPwdLoading(false);
    }
  };

  const selectedKey = '/' + location.pathname.split('/')[1];

  const role = user?.role;

  let menuItems: { key: string; icon: ReactNode; label: string }[];
  if (role === 'admin') {
    menuItems = [{ key: '/users', icon: <SettingOutlined />, label: '用户管理' }];
  } else {
    menuItems = [
      { key: '/positions', icon: <FileTextOutlined />, label: '职位管理' },
      { key: '/candidates', icon: <TeamOutlined />, label: '候选人管理' },
    ];
  }

  useEffect(() => {
    if (user?.role === 'admin' && location.pathname !== '/users') {
      navigate('/users', { replace: true });
    }
  }, [user, location.pathname, navigate]);

  const go = (key: string) => {
    navigate(key);
    setNavOpen(false);
  };

  const accountItems = [
    {
      key: 'password',
      icon: <LockOutlined />,
      label: '修改密码',
      onClick: () => setPwdOpen(true),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        logout();
        navigate('/login');
      },
    },
  ];

  const Brand = () => (
    <div className="brand-lockup">
      <div className="brand-mark">S</div>
      <div className="brand-text">
        <span className="brand-title">SmartHR</span>
        <span className="brand-subtitle">智能简历筛选</span>
      </div>
    </div>
  );

  const NavMenu = () => (
    <Menu
      className="app-menu"
      mode="inline"
      selectedKeys={[selectedKey]}
      items={menuItems}
      onClick={({ key }) => go(key)}
      style={{ border: 'none' }}
    />
  );

  return (
    <Layout className="app-shell">
      <Sider
        className="app-sider desktop-sider"
        width={210}
        style={{
          background: '#fff',
        }}
      >
        <Brand />
        <NavMenu />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
            <Button
              className="mobile-menu-button"
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setNavOpen(true)}
            />
            {isMobile ? <span className="app-header-title">SmartHR</span> : <span className="app-header-title">招聘工作台</span>}
          </div>
          <Dropdown menu={{ items: accountItems }} trigger={['click']}>
            <button
              type="button"
              className="app-header-user"
              style={{ border: 0, background: 'transparent', padding: 0, cursor: 'pointer' }}
            >
              <Avatar size={30} icon={<UserOutlined />} style={{ background: '#2563eb' }} />
              <span className="display-name">{user?.display_name || '当前用户'}</span>
            </button>
          </Dropdown>
          <Drawer
            title={null}
            placement="left"
            open={navOpen}
            onClose={() => setNavOpen(false)}
            width={286}
            styles={{ body: { padding: 0 }, header: { display: 'none' } }}
          >
            <Brand />
            <NavMenu />
          </Drawer>
          <Modal title="修改密码" open={pwdOpen} onOk={handleChangePassword} onCancel={() => { setPwdOpen(false); pwdForm.resetFields(); }} confirmLoading={pwdLoading} okText="确定" cancelText="取消">
            <p style={{ color: '#71717a', fontSize: 13, marginBottom: 16 }}>密码要求：至少8位，包含大小写字母、数字和特殊字符</p>
            <Form form={pwdForm} layout="vertical">
              <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}>
                <Input.Password />
              </Form.Item>
              <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 8, message: '密码至少8位' }]}>
                <Input.Password />
              </Form.Item>
              <Form.Item name="confirm_password" label="确认新密码" rules={[{ required: true, message: '请再次输入新密码' }]}>
                <Input.Password />
              </Form.Item>
            </Form>
          </Modal>
        </Header>
        <Content className="app-main">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
