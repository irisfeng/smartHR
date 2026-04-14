import { useState } from 'react';
import { Card, Form, Input, Button, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuthStore } from '../store/authStore';

export default function ForceChangePasswordPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);

  const onSubmit = async () => {
    const values = await form.validateFields();
    if (values.new_password !== values.confirm_password) {
      message.error('两次密码不一致');
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      const me = await api.get('/api/auth/me');
      setUser(me.data);
      message.success('密码修改成功');
      navigate('/', { replace: true });
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      message.error(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || '修改失败'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
      <Card style={{ width: 420, borderRadius: 12 }}>
        <h2 style={{ marginTop: 0 }}>请修改密码</h2>
        <p style={{ color: '#71717a', fontSize: 13 }}>为保护账户安全，请先修改当前密码。至少 8 位，包含大小写字母、数字和特殊字符。</p>
        <Form form={form} layout="vertical" onFinish={onSubmit}>
          <Form.Item name="old_password" label="当前密码" rules={[{ required: true }]}>
            <Input.Password autoFocus />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true }, { min: 8 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>提交</Button>
        </Form>
      </Card>
    </div>
  );
}
