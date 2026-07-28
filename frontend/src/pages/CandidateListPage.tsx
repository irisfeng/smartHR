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
      <div className="page-header">
        <div>
          <h2 className="page-title">候选人管理</h2>
          <p className="page-subtitle">按职位查看候选人池、AI 初筛结果和后续面试流转。</p>
        </div>
      </div>
      <Card className="surface-card">
        <p className="table-scroll-note">表格可左右滑动查看完整信息</p>
        <Table
          dataSource={positions}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 680 }}
        />
      </Card>
    </>
  );
}
