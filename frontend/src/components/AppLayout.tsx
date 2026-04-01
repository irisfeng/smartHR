import { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Modal, Form, Input, message } from 'antd';
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
            <a onClick={() => setPwdOpen(true)} style={{ marginLeft: 12, color: '#6366f1' }}>修改密码</a>
            <a onClick={() => { logout(); navigate('/login'); }} style={{ marginLeft: 12, color: '#6366f1' }}>退出</a>
          </span>
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
        <Content style={{ padding: 28, background: '#f8fafc' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
