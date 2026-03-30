import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Upload, Button, Progress, Tag, message } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import api from '../api';

interface BatchStatus {
  id: number;
  file_name: string;
  file_count: number;
  processed_count: number;
  status: string;
}

export default function UploadPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [positionTitle, setPositionTitle] = useState('');
  const [batches, setBatches] = useState<BatchStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api.get(`/api/positions/${id}`).then((res) => setPositionTitle(res.data.title)).catch(() => {});
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [id]);

  const pollBatch = (batchId: number) => {
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/api/upload-batches/${batchId}/status`);
        setBatches((prev) => prev.map((b) => (b.id === batchId ? res.data : b)));
        if (res.data.status !== 'processing') {
          clearInterval(interval);
          if (res.data.status === 'completed') {
            message.success(`${res.data.file_name} 处理完成`);
          }
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
    pollRef.current = interval;
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post(`/api/positions/${id}/upload`, formData);
      setBatches((prev) => [res.data, ...prev]);
      pollBatch(res.data.id);
      message.info('上传成功，开始处理...');
    } catch (e: any) {
      message.error(e.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
    return false;
  };

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/positions')} type="text" />
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
          上传简历 <span style={{ fontWeight: 400, color: '#a1a1aa', fontSize: 14 }}>— {positionTitle}</span>
        </h2>
      </div>

      <Card style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)', marginBottom: 20 }}>
        <Upload.Dragger
          accept=".pdf,.zip"
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploading}
          style={{ borderRadius: 12, background: '#fafaff' }}
        >
          <p style={{ fontSize: 36, opacity: 0.4, margin: '12px 0' }}>📄</p>
          <p style={{ color: '#71717a', margin: '0 0 4px' }}>点击或拖拽文件至此处</p>
          <p style={{ color: '#a1a1aa', fontSize: 12 }}>支持 .zip .pdf，ZIP 内自动解析所有 PDF</p>
        </Upload.Dragger>
      </Card>

      {batches.length > 0 && (
        <Card title="处理进度" style={{ borderRadius: 12, boxShadow: '0 1px 8px rgba(0,0,0,0.04)' }}>
          {batches.map((batch) => (
            <div key={batch.id} style={{
              padding: '12px 16px',
              background: batch.status === 'completed' ? '#f0fdf4'
                : batch.status === 'failed' ? '#fef2f2'
                : '#eef2ff',
              borderRadius: 8,
              marginBottom: 12,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
                <span>{batch.file_name} ({batch.file_count} 份)</span>
                <Tag color={
                  batch.status === 'completed' ? 'success'
                  : batch.status === 'failed' ? 'error'
                  : 'processing'
                }>
                  {batch.status === 'completed' ? '完成' : batch.status === 'failed' ? '失败' : `${batch.processed_count}/${batch.file_count}`}
                </Tag>
              </div>
              <Progress
                percent={batch.file_count > 0 ? Math.round((batch.processed_count / batch.file_count) * 100) : 0}
                size="small"
                strokeColor={batch.status === 'completed' ? '#22c55e' : batch.status === 'failed' ? '#ef4444' : '#6366f1'}
                showInfo={false}
              />
            </div>
          ))}
          <Button
            type="link"
            onClick={() => navigate(`/positions/${id}/candidates`)}
            style={{ padding: 0, color: '#6366f1' }}
          >
            查看候选人列表 →
          </Button>
        </Card>
      )}
    </>
  );
}
