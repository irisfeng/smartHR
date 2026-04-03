import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Button, Tag, Input, Modal, Form, Space, Select, message } from 'antd';
import { PlusOutlined, SearchOutlined, UploadOutlined, TeamOutlined } from '@ant-design/icons';
import api from '../api';
import { useAuthStore } from '../store/authStore';

interface Position {
  id: number;
  title: string;
  department: string;
  description: string;
  requirements: string;
  status: string;
  candidate_count: number;
  created_at: string;
}

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    setLoading(true);
    api.get('/api/positions')
      .then((res) => setPositions(res.data))
      .catch(() => message.error('获取职位列表失败'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = positions.filter(
    (p) => p.title.includes(search) || p.department.includes(search)
  );

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingId) {
        await api.put(`/api/positions/${editingId}`, values);
      } else {
        await api.post('/api/positions', values);
      }
      message.success(editingId ? '已更新' : '已创建');
      setModalOpen(false);
      setEditingId(null);
      form.resetFields();
      setLoading(true);
      api.get('/api/positions')
        .then((res) => setPositions(res.data))
        .catch(() => message.error('刷新列表失败'))
        .finally(() => setLoading(false));
    } catch (e: any) {
      if (e.errorFields) throw e;
      message.error(e.response?.data?.detail || '操作失败');
    }
  };

  const openEdit = (record: Position) => {
    setEditingId(record.id);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const columns = [
    { title: '职位名称', dataIndex: 'title', key: 'title', render: (t: string) => <span style={{ fontWeight: 500 }}>{t}</span> },
    { title: '部门', dataIndex: 'department', key: 'department' },
    {
      title: '候选人',
      dataIndex: 'candidate_count',
      key: 'candidate_count',
      render: (n: number) => <span style={{ color: n > 0 ? '#6366f1' : '#a1a1aa', fontWeight: 500 }}>{n}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => (
        <Tag color={s === 'open' ? 'purple' : 'default'} style={{ borderRadius: 20 }}>
          {s === 'open' ? '招聘中' : '已关闭'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Position) => (
        <Space size="small">
          <a onClick={() => navigate(`/positions/${record.id}/candidates`)}>
            <TeamOutlined /> 候选人
          </a>
          {(user?.role === 'hr' || user?.username === 'mgr_delivery' || user?.username === 'mgr_rd') && (
            <a onClick={() => navigate(`/positions/${record.id}/upload`)}>
              <UploadOutlined /> 上传
            </a>
          )}
          {user?.role === 'manager' && <a onClick={() => openEdit(record)}>编辑</a>}
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: '#18181b' }}>职位管理</h2>
        {user?.role === 'manager' && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => { setEditingId(null); form.resetFields(); setModalOpen(true); }}
            style={{ borderRadius: 8 }}
          >
            新建职位
          </Button>
        )}
      </div>
      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索职位..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 260, marginBottom: 16, borderRadius: 8 }}
        />
        <Table
          dataSource={filtered}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title={editingId ? '编辑职位' : '新建职位'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => { setModalOpen(false); setEditingId(null); }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="职位名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department" label="部门" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="职位描述 (JD)" rules={[{ required: true }]}>
            <Input.TextArea rows={6} placeholder="请输入完整的职位描述..." />
          </Form.Item>
          <Form.Item name="requirements" label="关键要求">
            <Input.TextArea rows={3} placeholder="如：本科以上，3年Java经验..." />
          </Form.Item>
          {editingId && (
            <Form.Item name="status" label="状态">
              <Select options={[{ label: '招聘中', value: 'open' }, { label: '已关闭', value: 'closed' }]} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </>
  );
}
