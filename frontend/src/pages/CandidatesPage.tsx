import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Select, Button, Space, Progress, Drawer, Descriptions, message } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import api from '../api';

interface Candidate {
  id: number;
  sequence_no: number;
  name: string;
  gender: string;
  age: number | null;
  phone: string;
  education: string;
  school: string;
  major: string;
  match_score: number | null;
  ai_recommendation: string;
  ai_summary: string;
  screening_result: string;
  first_interview_result: string;
  second_interview_result: string;
  status: string;
  recommend_date: string;
  recommend_channel: string;
  screening_date: string;
  leader_screening: string;
  interview_date: string;
  interview_time: string;
  interview_note: string;
  first_interview_note: string;
  second_interview_invite: string;
  second_interview_note: string;
  project_transfer: string;
}

interface CandidateDetail extends Candidate {
  id_number: string;
  parsed_text: string;
  ai_screening_result: Record<string, unknown> | null;
  resume_file_path: string;
  error_message: string;
}

const recColors: Record<string, string> = { '推荐': '#22c55e', '待定': '#f59e0b', '不推荐': '#ef4444' };

export default function CandidatesPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [positionTitle, setPositionTitle] = useState('');
  const [filterRec, setFilterRec] = useState<string | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<CandidateDetail | null>(null);

  useEffect(() => {
    api.get(`/api/positions/${id}`).then((res) => setPositionTitle(res.data.title)).catch(() => {});
    setLoading(true);
    const params: Record<string, string> = {};
    if (filterRec) params.recommendation = filterRec;
    api.get(`/api/positions/${id}/candidates`, { params })
      .then((res) => setCandidates(res.data))
      .catch(() => message.error('获取候选人列表失败'))
      .finally(() => setLoading(false));
  }, [id, filterRec]);

  const updateField = async (candidateId: number, field: string, value: string) => {
    await api.patch(`/api/candidates/${candidateId}`, { [field]: value });
    setCandidates((prev) =>
      prev.map((c) => (c.id === candidateId ? { ...c, [field]: value } : c))
    );
  };

  const openDetail = async (candidateId: number) => {
    const res = await api.get(`/api/candidates/${candidateId}`);
    setDetail(res.data);
    setDrawerOpen(true);
  };

  const exportExcel = async () => {
    const res = await api.get(`/api/positions/${id}/export`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${positionTitle}_候选人.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('导出成功');
  };

  const stats = {
    total: candidates.length,
    recommended: candidates.filter((c) => c.ai_recommendation === '推荐').length,
    pending: candidates.filter((c) => c.ai_recommendation === '待定').length,
    rejected: candidates.filter((c) => c.ai_recommendation === '不推荐').length,
  };

  const statusOptions = ['', '待邀约', '已邀约', '已拒绝'];
  const interviewOptions = ['', '通过', '未通过', '待定'];

  const columns = [
    { title: '#', dataIndex: 'sequence_no', width: 50 },
    { title: '姓名', dataIndex: 'name', width: 80, render: (t: string) => <span style={{ fontWeight: 500 }}>{t}</span> },
    { title: '学历', dataIndex: 'education', width: 60 },
    { title: '学校', dataIndex: 'school', width: 140, ellipsis: true },
    { title: '专业', dataIndex: 'major', width: 120, ellipsis: true },
    { title: '年龄', dataIndex: 'age', width: 50 },
    {
      title: 'AI 评估',
      dataIndex: 'ai_recommendation',
      width: 80,
      render: (r: string) => <span style={{ color: recColors[r] || '#999', fontWeight: 500 }}>{r || '—'}</span>,
    },
    {
      title: '匹配度',
      dataIndex: 'match_score',
      width: 100,
      sorter: (a: Candidate, b: Candidate) => (a.match_score || 0) - (b.match_score || 0),
      defaultSortOrder: 'descend' as const,
      render: (s: number | null) => s != null ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Progress
            percent={s}
            size="small"
            showInfo={false}
            strokeColor={s >= 70 ? '#22c55e' : s >= 40 ? '#f59e0b' : '#ef4444'}
            style={{ width: 50, margin: 0 }}
          />
          <span style={{ fontSize: 12, color: s >= 70 ? '#22c55e' : s >= 40 ? '#f59e0b' : '#ef4444' }}>{s}</span>
        </div>
      ) : '—',
    },
    {
      title: '邀约状态',
      dataIndex: 'screening_result',
      width: 110,
      render: (v: string, record: Candidate) => (
        <Select
          size="small"
          value={v || undefined}
          placeholder="—"
          style={{ width: 90 }}
          onChange={(val) => updateField(record.id, 'screening_result', val)}
          options={statusOptions.map((o) => ({ label: o || '—', value: o }))}
        />
      ),
    },
    {
      title: '一面',
      dataIndex: 'first_interview_result',
      width: 100,
      render: (v: string, record: Candidate) => (
        <Select
          size="small"
          value={v || undefined}
          placeholder="—"
          style={{ width: 80 }}
          onChange={(val) => updateField(record.id, 'first_interview_result', val)}
          options={interviewOptions.map((o) => ({ label: o || '—', value: o }))}
        />
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 60,
      render: (_: unknown, record: Candidate) => (
        <a onClick={() => openDetail(record.id)} style={{ color: '#6366f1', fontSize: 12 }}>详情</a>
      ),
    },
  ];

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/positions')} type="text" />
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{positionTitle}</h2>
        <Tag style={{ borderRadius: 20 }}>{stats.total}人</Tag>
        <Tag color="success" style={{ borderRadius: 20 }}>推荐 {stats.recommended}</Tag>
        <Tag color="warning" style={{ borderRadius: 20 }}>待定 {stats.pending}</Tag>
        <Tag color="error" style={{ borderRadius: 20 }}>不推荐 {stats.rejected}</Tag>
      </div>

      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space>
            <Select
              placeholder="AI推荐筛选"
              allowClear
              value={filterRec}
              onChange={setFilterRec}
              style={{ width: 140 }}
              options={[
                { label: '推荐', value: '推荐' },
                { label: '待定', value: '待定' },
                { label: '不推荐', value: '不推荐' },
              ]}
            />
          </Space>
          <Space>
            <Button icon={<UploadOutlined />} onClick={() => navigate(`/positions/${id}/upload`)}>上传简历</Button>
            <Button type="primary" icon={<DownloadOutlined />} onClick={exportExcel} style={{ background: '#6366f1' }}>
              导出 Excel
            </Button>
          </Space>
        </div>
        <Table
          dataSource={candidates}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 50 }}
          scroll={{ x: 1000 }}
          size="middle"
        />
      </Card>

      <Drawer
        title={detail?.name || '候选人详情'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={560}
      >
        {detail && (
          <>
            <Descriptions column={2} size="small" bordered style={{ marginBottom: 20 }}>
              <Descriptions.Item label="姓名">{detail.name}</Descriptions.Item>
              <Descriptions.Item label="性别">{detail.gender}</Descriptions.Item>
              <Descriptions.Item label="年龄">{detail.age}</Descriptions.Item>
              <Descriptions.Item label="电话">{detail.phone}</Descriptions.Item>
              <Descriptions.Item label="学历">{detail.education}</Descriptions.Item>
              <Descriptions.Item label="学校">{detail.school}</Descriptions.Item>
              <Descriptions.Item label="专业" span={2}>{detail.major}</Descriptions.Item>
            </Descriptions>

            <Card size="small" title="AI 筛选分析" style={{ marginBottom: 16, borderRadius: 8 }}>
              <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                <Tag color={recColors[detail.ai_recommendation] === '#22c55e' ? 'success' : recColors[detail.ai_recommendation] === '#ef4444' ? 'error' : 'warning'}>
                  {detail.ai_recommendation}
                </Tag>
                <span>匹配度: <strong>{detail.match_score}</strong>/100</span>
              </div>
              <p style={{ color: '#555', fontSize: 13 }}>{detail.ai_summary}</p>
              {detail.ai_screening_result && (
                <>
                  {(detail.ai_screening_result as any).strengths?.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <strong style={{ fontSize: 12, color: '#22c55e' }}>优势：</strong>
                      {(detail.ai_screening_result as any).strengths.map((s: string, i: number) => (
                        <Tag key={i} color="success" style={{ margin: 2 }}>{s}</Tag>
                      ))}
                    </div>
                  )}
                  {(detail.ai_screening_result as any).concerns?.length > 0 && (
                    <div>
                      <strong style={{ fontSize: 12, color: '#f59e0b' }}>顾虑：</strong>
                      {(detail.ai_screening_result as any).concerns.map((s: string, i: number) => (
                        <Tag key={i} color="warning" style={{ margin: 2 }}>{s}</Tag>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Card>

            <Button
              type="link"
              onClick={async () => {
                try {
                  const res = await api.get(`/api/candidates/${detail.id}/resume`, { responseType: 'blob' });
                  const url = URL.createObjectURL(res.data);
                  window.open(url, '_blank');
                } catch {
                  message.error('获取简历失败');
                }
              }}
              style={{ padding: 0, color: '#6366f1' }}
            >
              查看原始简历 PDF →
            </Button>
          </>
        )}
      </Drawer>
    </>
  );
}