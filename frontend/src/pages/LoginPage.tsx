import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Modal, message } from 'antd';
import api from '../api';
import { useAuthStore } from '../store/authStore';

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [pwdOpen, setPwdOpen] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [loginPassword, setLoginPassword] = useState('');
  const [pwdForm] = Form.useForm();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);

  const goToDashboard = async () => {
    const me = await api.get('/api/auth/me');
    setUser(me.data);
    navigate('/');
  };

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await api.post('/api/auth/login', values);
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      if (res.data.must_change_password) {
        setLoginPassword(values.password);
        setPwdOpen(true);
      } else {
        await goToDashboard();
      }
    } catch {
      message.error('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async () => {
    const values = await pwdForm.validateFields();
    if (values.new_password !== values.confirm_password) {
      message.error('两次密码不一致');
      return;
    }
    setPwdLoading(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: loginPassword,
        new_password: values.new_password,
      });
      message.success('密码修改成功');
      setPwdOpen(false);
      await goToDashboard();
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

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)',
    }}>
      <Card style={{ width: 380, borderRadius: 16, boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{ color: '#6366f1', fontSize: 26, letterSpacing: 2, margin: 0 }}>SmartHR</h1>
          <p style={{ color: '#a1a1aa', fontSize: 13, marginTop: 6 }}>智能简历筛选系统</p>
        </div>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input size="large" style={{ borderRadius: 10 }} />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password size="large" style={{ borderRadius: 10 }} />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            block
            size="large"
            loading={loading}
            style={{ borderRadius: 10, background: '#6366f1', borderColor: '#6366f1', letterSpacing: 2 }}
          >
            登 录
          </Button>
        </Form>
      </Card>
      <Modal
        title="首次登录请修改密码"
        open={pwdOpen}
        onOk={handleChangePassword}
        closable={false}
        maskClosable={false}
        keyboard={false}
        confirmLoading={pwdLoading}
        okText="确认修改"
        cancelButtonProps={{ style: { display: 'none' } }}
      >
        <p style={{ color: '#71717a', fontSize: 13, marginBottom: 16 }}>
          密码要求：至少8位，包含大小写字母、数字和特殊字符
        </p>
        <Form form={pwdForm} layout="vertical">
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 8, message: '密码至少8位' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" rules={[{ required: true, message: '请再次输入新密码' }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
