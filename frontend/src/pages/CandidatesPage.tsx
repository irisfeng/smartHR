import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Table, Tag, Select, Button, Space, Progress, Drawer, Descriptions,
  Input, InputNumber, Tooltip, Popconfirm, message,
} from 'antd';
import {
  ArrowLeftOutlined, DownloadOutlined, UploadOutlined,
  EditOutlined, WarningOutlined, DeleteOutlined,
} from '@ant-design/icons';
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
  parse_quality: string;
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

interface AiScreeningResult {
  strengths?: string[];
  concerns?: string[];
  analysis?: string;
  [key: string]: unknown;
}

interface CandidateDetail extends Candidate {
  id_number: string;
  parsed_text: string;
  ai_screening_result: Record<string, unknown> | null;
  ai_analysis: string;
  resume_file_path: string;
  error_message: string;
}

const recColors: Record<string, string> = { '推荐': '#22c55e', '待定': '#f59e0b', '不推荐': '#ef4444' };
const educationOptions = ['本科', '大专', '硕士', '博士', '专科', '中专', '高中', '初中'];

// Editable cell component
function EditableCell({
  value,
  onSave,
  type = 'text' as 'text' | 'number' | 'select',
  options,
  style,
}: {
  value: string | number | null;
  onSave: (val: string | number | null) => void;
  type?: 'text' | 'number' | 'select';
  options?: string[];
  style?: React.CSSProperties;
}) {
  const [editing, setEditing] = useState(false);
  const [temp, setTemp] = useState(value ?? '');

  if (editing) {
    const handleSave = () => {
      const saveVal = type === 'number' ? (temp === '' ? null : Number(temp)) : String(temp);
      onSave(saveVal);
      setEditing(false);
    };

    if (type === 'select' && options) {
      return (
        <Select
          size="small"
          value={String(temp)}
          style={{ width: '100%' }}
          onChange={(v) => { setTemp(v); onSave(v); setEditing(false); }}
          onBlur={() => setEditing(false)}
          options={options.map((o) => ({ label: o, value: o }))}
          autoFocus
          open
        />
      );
    }

    const InputComponent = type === 'number' ? InputNumber : Input;
    return (
      <InputComponent
        size="small"
        value={temp}
        onChange={(e: any) => setTemp(e.target?.value ?? e)}
        onPressEnter={handleSave}
        onBlur={handleSave}
        autoFocus
        style={{ width: '100%', ...style }}
      />
    );
  }

  return (
    <div
      style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, ...style }}
      onClick={() => setEditing(true)}
    >
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {value || '—'}
      </span>
      <EditOutlined style={{ color: '#d4d4d8', fontSize: 11, opacity: 0, transition: 'opacity 0.2s' }} className="edit-icon" />
      <style>{`
        div:hover .edit-icon { opacity: 1 !important; }
      `}</style>
    </div>
  );
}

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

  const updateField = async (candidateId: number, field: string, value: string | number | null) => {
    try {
      await api.patch(`/api/candidates/${candidateId}`, { [field]: value });
      setCandidates((prev) =>
        prev.map((c) => (c.id === candidateId ? { ...c, [field]: value } : c))
      );
      // Also update detail if drawer is open for this candidate
      if (detail?.id === candidateId) {
        setDetail((prev) => prev ? { ...prev, [field]: value } : null);
      }
    } catch (e: any) {
      message.error(e.response?.data?.detail || '更新失败');
    }
  };

  const openDetail = async (candidateId: number) => {
    try {
      const res = await api.get(`/api/candidates/${candidateId}`);
      setDetail(res.data);
      setDrawerOpen(true);
    } catch (e: any) {
      message.error(e.response?.data?.detail || '获取详情失败');
    }
  };

  const exportExcel = async () => {
    try {
      const res = await api.get(`/api/positions/${id}/export`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${positionTitle}_候选人.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (e: any) {
      message.error(e.response?.data?.detail || '导出失败');
    }
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
    {
      title: '#',
      width: 50,
      render: (_: unknown, __: Candidate, index: number) => index + 1,
    },
    {
      title: '姓名',
      dataIndex: 'name',
      width: 100,
      render: (v: string, record: Candidate) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <EditableCell value={v} onSave={(val) => updateField(record.id, 'name', val)} style={{ fontWeight: 500 }} />
          {record.parse_quality === 'poor' && (
            <Tooltip title="简历解析质量差，建议人工核对">
              <WarningOutlined style={{ color: '#f59e0b', fontSize: 13 }} />
            </Tooltip>
          )}
        </div>
      ),
    },
    {
      title: '学历',
      dataIndex: 'education',
      width: 80,
      render: (v: string, record: Candidate) => (
        <EditableCell
          value={v}
          onSave={(val) => updateField(record.id, 'education', val)}
          type="select"
          options={educationOptions}
        />
      ),
    },
    {
      title: '学校',
      dataIndex: 'school',
      width: 150,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'school', val)} />
      ),
    },
    {
      title: '专业',
      dataIndex: 'major',
      width: 120,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'major', val)} />
      ),
    },
    {
      title: '年龄',
      dataIndex: 'age',
      width: 70,
      render: (v: number | null, record: Candidate) => (
        <EditableCell
          value={v}
          onSave={(val) => updateField(record.id, 'age', val)}
          type="number"
        />
      ),
    },
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
            <Popconfirm title="确定清空所有候选人？" onConfirm={async () => { await api.delete(`/api/positions/${id}/candidates`); setCandidates([]); message.success('已清空'); }}>
              <Button icon={<DeleteOutlined />} danger disabled={candidates.length === 0}>清空候选人</Button>
            </Popconfirm>
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
          rowClassName={(record) => record?.parse_quality === 'poor' ? 'poor-quality-row' : ''}
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
              <Descriptions.Item label="姓名">
                <EditableCell value={detail.name} onSave={(v) => updateField(detail.id, 'name', v)} />
              </Descriptions.Item>
              <Descriptions.Item label="性别">
                <EditableCell value={detail.gender} onSave={(v) => updateField(detail.id, 'gender', v)} />
              </Descriptions.Item>
              <Descriptions.Item label="年龄">
                <EditableCell value={String(detail.age ?? '')} onSave={(v) => updateField(detail.id, 'age', v)} type="number" />
              </Descriptions.Item>
              <Descriptions.Item label="电话">
                <EditableCell value={detail.phone} onSave={(v) => updateField(detail.id, 'phone', v)} />
              </Descriptions.Item>
              <Descriptions.Item label="学历">
                <EditableCell value={detail.education} onSave={(v) => updateField(detail.id, 'education', v)} type="select" options={educationOptions} />
              </Descriptions.Item>
              <Descriptions.Item label="学校">
                <EditableCell value={detail.school} onSave={(v) => updateField(detail.id, 'school', v)} />
              </Descriptions.Item>
              <Descriptions.Item label="专业" span={2}>
                <EditableCell value={detail.major} onSave={(v) => updateField(detail.id, 'major', v)} />
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="AI 筛选分析" style={{ marginBottom: 16, borderRadius: 8 }}>
              <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                <Tag color={recColors[detail.ai_recommendation] === '#22c55e' ? 'success' : recColors[detail.ai_recommendation] === '#ef4444' ? 'error' : 'warning'}>
                  {detail.ai_recommendation}
                </Tag>
                <span>匹配度: <strong>{detail.match_score}</strong>/100</span>
                {detail.parse_quality === 'poor' && (
                  <Tag color="warning" icon={<WarningOutlined />}>解析质量差</Tag>
                )}
              </div>
              {/* Show AI analysis if available */}
              {detail.ai_screening_result && (detail.ai_screening_result as AiScreeningResult).analysis && (
                <p style={{ color: '#666', fontSize: 12, fontStyle: 'italic', marginBottom: 8 }}>
                  {(detail.ai_screening_result as AiScreeningResult).analysis}
                </p>
              )}
              <p style={{ color: '#555', fontSize: 13 }}>{detail.ai_summary}</p>
              {detail.ai_screening_result && (
                <>
                  {((detail.ai_screening_result as AiScreeningResult).strengths?.length ?? 0) > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <strong style={{ fontSize: 12, color: '#22c55e' }}>优势：</strong>
                      {(detail.ai_screening_result as AiScreeningResult).strengths!.map((s: string, i: number) => (
                        <Tag key={i} color="success" style={{ margin: 2 }}>{s}</Tag>
                      ))}
                    </div>
                  )}
                  {((detail.ai_screening_result as AiScreeningResult).concerns?.length ?? 0) > 0 && (
                    <div>
                      <strong style={{ fontSize: 12, color: '#f59e0b' }}>顾虑：</strong>
                      {(detail.ai_screening_result as AiScreeningResult).concerns!.map((s: string, i: number) => (
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
              查看原始简历 PDF &rarr;
            </Button>
          </>
        )}
      </Drawer>

      <style>{`
        .poor-quality-row {
          background: #fffbeb !important;
        }
        .poor-quality-row:hover > td {
          background: #fef3c7 !important;
        }
      `}</style>
    </>
  );
}
