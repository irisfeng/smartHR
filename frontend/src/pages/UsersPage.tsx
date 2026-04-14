import { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Tag, Popconfirm, Space, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../api';
import { useAuthStore } from '../store/authStore';

interface UserRecord {
  id: number;
  username: string;
  role: string;
  display_name: string;
  created_at: string;
  must_change_password?: boolean;
}

const ROLE_OPTIONS = [
  { label: 'HR专员', value: 'hr' },
  { label: '用人经理', value: 'manager' },
  { label: '系统管理员', value: 'admin' },
];

const ROLE_STYLE: Record<string, { color: string; label: string }> = {
  admin: { color: 'red', label: '系统管理员' },
  manager: { color: 'purple', label: '用人经理' },
  hr: { color: 'blue', label: 'HR专员' },
};

export default function UsersPage() {
  const currentUser = useAuthStore((s) => s.user);
  const isAdmin = currentUser?.role === 'admin';

  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();

  // Edit modal
  const [editOpen, setEditOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [editingId, setEditingId] = useState<number | null>(null);

  // Reset password modal
  const [resetOpen, setResetOpen] = useState(false);
  const [resetForm] = Form.useForm();
  const [resetTargetId, setResetTargetId] = useState<number | null>(null);

  const reload = () => {
    setLoading(true);
    api.get('/api/users')
      .then((res) => setUsers(res.data))
      .catch(() => message.error('获取用户列表失败'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { reload(); }, []);

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields();
      await api.post('/api/users', values);
      message.success('用户已创建，首次登录将被要求修改密码');
      setCreateOpen(false);
      createForm.resetFields();
      reload();
    } catch (e: any) {
      if (e.errorFields) throw e;
      const detail = e.response?.data?.detail;
      message.error(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || '创建失败'));
    }
  };

  const openEdit = (record: UserRecord) => {
    setEditingId(record.id);
    editForm.setFieldsValue({ display_name: record.display_name, role: record.role });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    try {
      const values = await editForm.validateFields();
      await api.put(`/api/users/${editingId}`, values);
      message.success('已更新');
      setEditOpen(false);
      reload();
    } catch (e: any) {
      if (e.errorFields) throw e;
      const detail = e.response?.data?.detail;
      message.error(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || '更新失败'));
    }
  };

  const openResetPwd = (record: UserRecord) => {
    setResetTargetId(record.id);
    resetForm.resetFields();
    setResetOpen(true);
  };

  const handleResetPassword = async () => {
    try {
      const values = await resetForm.validateFields();
      await api.post(`/api/users/${resetTargetId}/reset-password`, {
        new_password: values.new_password,
      });
      message.success('密码已重置。请把临时密码告知用户，其下次登录将被要求修改');
      setResetOpen(false);
    } catch (e: any) {
      if (e.errorFields) throw e;
      const detail = e.response?.data?.detail;
      message.error(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || '重置失败'));
    }
  };

  const handleDelete = async (userId: number) => {
    try {
      await api.delete(`/api/users/${userId}`);
      message.success('已删除');
      reload();
    } catch (e: any) {
      const detail = e.response?.data?.detail;
      message.error(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : (detail || '删除失败'));
    }
  };

  const columns = [
    { title: '用户名', dataIndex: 'username' },
    { title: '显示名', dataIndex: 'display_name' },
    {
      title: '角色',
      dataIndex: 'role',
      render: (r: string) => {
        const { color, label } = ROLE_STYLE[r] ?? { color: 'default', label: r };
        return <Tag color={color} style={{ borderRadius: 20 }}>{label}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: UserRecord) => {
        if (!isAdmin) return null;
        const isSelf = currentUser?.id === record.id;
        return (
          <Space size="small">
            <a onClick={() => openEdit(record)}>编辑</a>
            {!isSelf && <a onClick={() => openResetPwd(record)}>重置密码</a>}
            {!isSelf && (
              <Popconfirm title="确认删除该账号？" onConfirm={() => handleDelete(record.id)}>
                <a style={{ color: '#ef4444' }}>删除</a>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>用户管理</h2>
        {isAdmin && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)} style={{ borderRadius: 8 }}>
            新建用户
          </Button>
        )}
      </div>

      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <Table dataSource={users} columns={columns} rowKey="id" loading={loading} pagination={false} />
      </Card>

      {/* Create modal */}
      <Modal
        title="新建用户"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => setCreateOpen(false)}
        okText="创建"
        cancelText="取消"
      >
        <p style={{ color: '#71717a', fontSize: 13, marginBottom: 16 }}>新用户首次登录时将被要求修改初始密码。</p>
        <Form form={createForm} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true }, { min: 2, max: 32 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="初始密码" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit modal */}
      <Modal
        title="编辑用户"
        open={editOpen}
        onOk={handleEdit}
        onCancel={() => setEditOpen(false)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true }, { min: 1, max: 32 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Reset password modal */}
      <Modal
        title="重置密码"
        open={resetOpen}
        onOk={handleResetPassword}
        onCancel={() => setResetOpen(false)}
        okText="重置"
        cancelText="取消"
      >
        <p style={{ color: '#71717a', fontSize: 13, marginBottom: 16 }}>
          至少 8 位，含大小写字母、数字和特殊字符。重置后该用户下次登录必须自行修改密码。
        </p>
        <Form form={resetForm} layout="vertical">
          <Form.Item name="new_password" label="新密码" rules={[{ required: true }, { min: 8, message: '密码至少8位' }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
