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
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 401) {
        message.error('用户名或密码错误');
      } else if (status) {
        const detail = e?.response?.data?.detail;
        message.error(`登录失败（${status}）${typeof detail === 'string' ? '：' + detail : ''}`);
      } else {
        message.error('网络异常，请检查后端服务是否运行');
      }
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
    <div className="login-screen">
      <section className="login-copy">
        <div className="brand-lockup" style={{ padding: 0, border: 0, marginBottom: 30 }}>
          <div className="brand-mark">S</div>
          <div className="brand-text">
            <span className="brand-title">SmartHR</span>
            <span className="brand-subtitle">智能简历筛选系统</span>
          </div>
        </div>
        <h1>
          <span>把简历筛选流程</span>
          <span>收进一个工作台</span>
        </h1>
        <p>职位、批量上传、AI 初筛、候选人流转和 Excel 导出集中管理，保留人工复核空间。</p>
        <div className="login-proof">
          <span>职位维度管理</span>
          <span>PDF / ZIP 批量解析</span>
          <span>候选人表格可编辑</span>
        </div>
      </section>
      <Card className="login-card">
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h2 style={{ color: '#111827', fontSize: 24, fontWeight: 760, margin: 0 }}>登录工作台</h2>
          <p style={{ color: '#64748b', fontSize: 13, marginTop: 8 }}>使用你的 SmartHR 账号继续</p>
        </div>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input size="large" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password size="large" />
          </Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            block
            size="large"
            loading={loading}
            style={{ letterSpacing: 1 }}
          >
            登录
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
