import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, message } from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import api from '../api';

interface Position {
  id: number;
  title: string;
  department: string;
  status: string;
  candidate_count: number;
}

export default function CandidateListPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    api.get('/api/positions')
      .then((res) => setPositions(res.data))
      .catch(() => message.error('获取职位列表失败'))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { title: '职位名称', dataIndex: 'title', key: 'title', render: (t: string) => <span style={{ fontWeight: 500 }}>{t}</span> },
    { title: '部门', dataIndex: 'department', key: 'department' },
    {
      title: '候选人数',
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
        <a onClick={() => navigate(`/positions/${record.id}/candidates`)}>
          <TeamOutlined /> 查看候选人
        </a>
      ),
    },
  ];

  return (
    <>
      <h2 style={{ margin: '0 0 20px', fontSize: 18, fontWeight: 600, color: '#18181b' }}>候选人管理</h2>
      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <Table
          dataSource={positions}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>
    </>
  );
}
