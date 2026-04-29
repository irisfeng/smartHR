import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Table, Tag, Select, Button, Space, Progress, Drawer, Descriptions,
  Input, InputNumber, Tooltip, Popconfirm, Collapse, message,
} from 'antd';
import {
  ArrowLeftOutlined, DownloadOutlined, UploadOutlined,
  EditOutlined, WarningOutlined, DeleteOutlined, InfoCircleOutlined,
  EyeOutlined, EyeInvisibleOutlined,
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
  // Recruitment pipeline fields
  recommend_date: string;
  recommend_channel: string;
  id_number: string;
  screening_date: string;
  leader_screening: string;
  screening_result: string;
  interview_date: string;
  interview_time: string;
  interview_note: string;
  first_interview_result: string;
  evaluation_result: string;
  first_interview_note: string;
  second_interview_invite: string;
  second_interview_result: string;
  second_interview_note: string;
  project_transfer: string;
  status: string;
}

interface PositionDetail {
  id: number;
  title: string;
  department: string;
  description: string;
  requirements: string;
  status: string;
}

interface AiScreeningResult {
  strengths?: string[];
  concerns?: string[];
  analysis?: string;
  [key: string]: unknown;
}

interface CandidateDetail extends Candidate {
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
          options={options.map((o) => ({ label: o || '—', value: o }))}
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

// Masked cell for sensitive data — click eye to reveal, click text to edit
// maskType: 'id' = show first4/last4, 'phone' = show first3/last4
function MaskedCell({
  value,
  onSave,
  maskType = 'id',
}: {
  value: string | null;
  onSave: (val: string | number | null) => void;
  maskType?: 'id' | 'phone';
}) {
  const [visible, setVisible] = useState(false);
  const [editing, setEditing] = useState(false);
  const [temp, setTemp] = useState(value ?? '');

  if (editing) {
    const handleSave = () => { onSave(String(temp)); setEditing(false); };
    return (
      <Input
        size="small"
        value={temp}
        onChange={(e) => setTemp(e.target.value)}
        onPressEnter={handleSave}
        onBlur={handleSave}
        autoFocus
        style={{ width: '100%' }}
      />
    );
  }

  const maskValue = (v: string) => {
    if (maskType === 'phone' && v.length >= 7) {
      return v.slice(0, 3) + '****' + v.slice(-4);
    }
    return v.replace(/^(.{4})(.+)(.{4})$/, (_, a, m, b) => a + '*'.repeat(m.length) + b);
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span
        style={{ cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12 }}
        onClick={() => setEditing(true)}
      >
        {value ? (visible ? value : maskValue(value)) : '—'}
      </span>
      {value && (
        <span style={{ cursor: 'pointer', color: '#a1a1aa', fontSize: 12 }} onClick={() => setVisible(!visible)}>
          {visible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
        </span>
      )}
    </div>
  );
}

export default function CandidatesPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [position, setPosition] = useState<PositionDetail | null>(null);
  const [filterRec, setFilterRec] = useState<string | undefined>();
  const [searchText, setSearchText] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState<CandidateDetail | null>(null);

  useEffect(() => {
    api.get(`/api/positions/${id}`).then((res) => setPosition(res.data)).catch(() => {});
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
      a.download = `${position?.title || '职位'}_候选人.xlsx`;
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
  // evaluationOptions removed — evaluation_result is free text now

  // All columns matching Excel export order, plus AI fields, all editable
  const columns = [
    {
      title: '#',
      dataIndex: 'sequence_no',
      width: 50,
      fixed: 'left' as const,
      render: (_: unknown, __: Candidate, index: number) => index + 1,
    },
    {
      title: '姓名',
      dataIndex: 'name',
      width: 90,
      fixed: 'left' as const,
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
      title: '身份证',
      dataIndex: 'id_number',
      width: 160,
      render: (v: string, record: Candidate) => (
        <MaskedCell value={v} onSave={(val) => updateField(record.id, 'id_number', val)} />
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
      title: '推荐日期',
      dataIndex: 'recommend_date',
      width: 120,
      sorter: (a: Candidate, b: Candidate) =>
        (a.recommend_date || '\uffff').localeCompare(b.recommend_date || '\uffff'),
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'recommend_date', val)} />
      ),
    },
    {
      title: '推荐渠道',
      dataIndex: 'recommend_channel',
      width: 100,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'recommend_channel', val)} />
      ),
    },
    {
      title: '年龄',
      dataIndex: 'age',
      width: 65,
      sorter: (a: Candidate, b: Candidate) =>
        (a.age ?? Number.POSITIVE_INFINITY) - (b.age ?? Number.POSITIVE_INFINITY),
      render: (v: number | null, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'age', val)} type="number" />
      ),
    },
    {
      title: '性别',
      dataIndex: 'gender',
      width: 65,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'gender', val)} type="select" options={['', '男', '女']} />
      ),
    },
    {
      title: '电话',
      dataIndex: 'phone',
      width: 140,
      render: (v: string, record: Candidate) => (
        <MaskedCell value={v} onSave={(val) => updateField(record.id, 'phone', val)} maskType="phone" />
      ),
    },
    {
      title: '学历',
      dataIndex: 'education',
      width: 80,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'education', val)} type="select" options={educationOptions} />
      ),
    },
    {
      title: '毕业学校',
      dataIndex: 'school',
      width: 130,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'school', val)} />
      ),
    },
    {
      title: '专业',
      dataIndex: 'major',
      width: 110,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'major', val)} />
      ),
    },
    {
      title: '筛选日期',
      dataIndex: 'screening_date',
      width: 100,
      sorter: (a: Candidate, b: Candidate) =>
        (a.screening_date || '\uffff').localeCompare(b.screening_date || '\uffff'),
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'screening_date', val)} />
      ),
    },
    {
      title: '领导初筛',
      dataIndex: 'leader_screening',
      width: 100,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'leader_screening', val)} />
      ),
    },
    {
      title: '筛选邀约',
      dataIndex: 'screening_result',
      width: 100,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'screening_result', val)} type="select" options={statusOptions} />
      ),
    },
    {
      title: '面试日期',
      dataIndex: 'interview_date',
      width: 100,
      sorter: (a: Candidate, b: Candidate) =>
        (a.interview_date || '\uffff').localeCompare(b.interview_date || '\uffff'),
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'interview_date', val)} />
      ),
    },
    {
      title: '面试时间',
      dataIndex: 'interview_time',
      width: 90,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'interview_time', val)} />
      ),
    },
    {
      title: '备注',
      dataIndex: 'interview_note',
      width: 120,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'interview_note', val)} />
      ),
    },
    {
      title: '一面结果',
      dataIndex: 'first_interview_result',
      width: 100,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'first_interview_result', val)} type="select" options={interviewOptions} />
      ),
    },
    {
      title: '评估结果',
      dataIndex: 'evaluation_result',
      width: 140,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'evaluation_result', val)} />
      ),
    },
    {
      title: '一面备注',
      dataIndex: 'first_interview_note',
      width: 120,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'first_interview_note', val)} />
      ),
    },
    {
      title: '二面邀约',
      dataIndex: 'second_interview_invite',
      width: 100,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'second_interview_invite', val)} />
      ),
    },
    {
      title: '二面结果',
      dataIndex: 'second_interview_result',
      width: 100,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'second_interview_result', val)} type="select" options={interviewOptions} />
      ),
    },
    {
      title: '二面备注',
      dataIndex: 'second_interview_note',
      width: 120,
      ellipsis: true,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'second_interview_note', val)} />
      ),
    },
    {
      title: '转项目',
      dataIndex: 'project_transfer',
      width: 100,
      render: (v: string, record: Candidate) => (
        <EditableCell value={v} onSave={(val) => updateField(record.id, 'project_transfer', val)} />
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 110,
      fixed: 'right' as const,
      render: (_: unknown, record: Candidate) => (
        <Space size={8}>
          <a onClick={() => openDetail(record.id)} style={{ color: '#6366f1', fontSize: 12 }}>详情</a>
          <Popconfirm
            title="删除该候选人？"
            description="此操作不可恢复"
            okText="删除"
            okButtonProps={{ danger: true }}
            cancelText="取消"
            onConfirm={async () => {
              try {
                await api.delete(`/api/candidates/${record.id}`);
                setCandidates((prev) => prev.filter((c) => c.id !== record.id));
                message.success('已删除');
              } catch (e: any) {
                message.error(e.response?.data?.detail || '删除失败');
              }
            }}
          >
            <a style={{ color: '#ef4444', fontSize: 12 }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Calculate total scroll width from column widths
  const totalScrollX = columns.reduce((sum, col) => sum + (col.width || 100), 0);

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/positions')} type="text" />
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>{position?.title || ''}</h2>
        <Tag style={{ borderRadius: 20 }}>{stats.total}人</Tag>
        <Tag color="success" style={{ borderRadius: 20 }}>推荐 {stats.recommended}</Tag>
        <Tag color="warning" style={{ borderRadius: 20 }}>待定 {stats.pending}</Tag>
        <Tag color="error" style={{ borderRadius: 20 }}>不推荐 {stats.rejected}</Tag>
      </div>

      {/* Position JD & Requirements — collapsible, so HR can see what the manager wrote */}
      {position && (position.description || position.requirements) && (
        <Collapse
          size="small"
          style={{ marginBottom: 16, borderRadius: 8 }}
          items={[{
            key: 'jd',
            label: (
              <span style={{ fontSize: 13, color: '#6366f1' }}>
                <InfoCircleOutlined style={{ marginRight: 6 }} />
                查看岗位需求 (JD)
              </span>
            ),
            children: (
              <Descriptions column={1} size="small" bordered>
                <Descriptions.Item label="职位描述 (JD)">
                  <div style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{position.description || '—'}</div>
                </Descriptions.Item>
                {position.requirements && (
                  <Descriptions.Item label="关键要求">
                    <div style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{position.requirements}</div>
                  </Descriptions.Item>
                )}
              </Descriptions>
            ),
          }]}
        />
      )}

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
            <Input.Search
              placeholder="搜索姓名 / 学校 / 专业"
              allowClear
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 260 }}
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
          dataSource={(() => {
            const q = searchText.trim().toLowerCase();
            if (!q) return candidates;
            return candidates.filter((c) =>
              [c.name, c.school, c.major].some((v) => (v || '').toLowerCase().includes(q))
            );
          })()}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ defaultPageSize: 50, showSizeChanger: true, pageSizeOptions: [20, 50, 100, 200] }}
          scroll={{ x: totalScrollX }}
          size="small"
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
