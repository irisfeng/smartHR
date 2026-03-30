import { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Tag, Popconfirm, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import api from '../api';

interface UserRecord {
  id: number;
  username: string;
  role: string;
  display_name: string;
  created_at: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/users');
      setUsers(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async () => {
    const values = await form.validateFields();
    await api.post('/api/users', values);
    message.success('用户已创建');
    setModalOpen(false);
    form.resetFields();
    fetchUsers();
  };

  const handleDelete = async (userId: number) => {
    await api.delete(`/api/users/${userId}`);
    message.success('已删除');
    fetchUsers();
  };

  const columns = [
    { title: '用户名', dataIndex: 'username' },
    { title: '显示名', dataIndex: 'display_name' },
    {
      title: '角色',
      dataIndex: 'role',
      render: (r: string) => (
        <Tag color={r === 'manager' ? 'purple' : 'blue'} style={{ borderRadius: 20 }}>
          {r === 'manager' ? '用人经理' : 'HR专员'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: UserRecord) => (
        <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
          <a style={{ color: '#ef4444' }}>删除</a>
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>用户管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)} style={{ borderRadius: 8 }}>
          新建用户
        </Button>
      </div>

      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <Table dataSource={users} columns={columns} rowKey="id" loading={loading} pagination={false} />
      </Card>

      <Modal
        title="新建用户"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 4 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={[{ label: 'HR专员', value: 'hr' }, { label: '用人经理', value: 'manager' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
