import { useQuery } from '@tanstack/react-query'
import { Card, Col, Row, Space, Spin, Tag, Timeline, Typography } from 'antd'
import {
  BranchesOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  ProjectOutlined,
} from '@ant-design/icons'
import request from 'axios'
import { useMemo } from 'react'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:5409'

type ProposalArtifactTasks = {
  total: number
  completed: number
}

type ProposalArtifacts = {
  proposal?: string
  design?: string
  tasks?: ProposalArtifactTasks
}

type Proposal = {
  dir: string
  name: string
  created: string
  status: string
  artifacts?: ProposalArtifacts
  layers?: string[]
  platforms?: string[]
  applyReady?: boolean
}

const LAYER_COLORS: Record<string, string> = {
  cli: 'blue',
  api: 'geekblue',
  frontend: 'purple',
}

const STATUS_META: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  proposed: { color: 'default', icon: <ClockCircleOutlined />, label: '已提案' },
  'in-progress': { color: 'processing', icon: <ExperimentOutlined />, label: '进行中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, label: '已完成' },
  archived: { color: 'default', icon: <BranchesOutlined />, label: '已归档' },
}

function ProposalsPage() {
  const { data: proposals = [], isLoading } = useQuery<Proposal[]>({
    queryKey: ['proposals'],
    queryFn: async () => {
      const res = await request.get(`${API_BASE}/api/proposals`)
      return res.data.data ?? []
    },
    refetchInterval: 30_000,
  })

  const sorted = useMemo(
    () => [...proposals].sort((a, b) => b.created.localeCompare(a.created)),
    [proposals],
  )

  return (
    <div style={{ padding: 0 }}>
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card
            title={
              <Space>
                <ProjectOutlined />
                <span>变更提案</span>
                <Tag>{proposals.length}</Tag>
              </Space>
            }
          >
            {isLoading ? (
              <div style={{ textAlign: 'center', padding: 48 }}>
                <Spin />
              </div>
            ) : sorted.length === 0 ? (
              <Typography.Text type="secondary">
                暂无提案。在终端运行 <Typography.Text code>/opsx-propose "你的想法"</Typography.Text> 来创建第一个提案。
              </Typography.Text>
            ) : (
              <Timeline
                items={sorted.map((p) => {
                  const meta = STATUS_META[p.status] ?? STATUS_META.proposed
                  return {
                    color: meta.color,
                    children: (
                      <Card
                        size="small"
                        style={{ marginBottom: 8 }}
                        title={
                          <Space>
                            {meta.icon}
                            <Typography.Text strong>{p.name}</Typography.Text>
                            <Tag color={meta.color}>{meta.label}</Tag>
                          </Space>
                        }
                      >
                        <Space direction="vertical" style={{ width: '100%' }} size="small">
                          {/* Summary */}
                          {p.artifacts?.proposal && (
                            <Typography.Paragraph
                              type="secondary"
                              ellipsis={{ rows: 2, expandable: true }}
                              style={{ margin: 0, fontSize: 13 }}
                            >
                              {p.artifacts.proposal}
                            </Typography.Paragraph>
                          )}

                          {/* Layer tags */}
                          {p.layers && p.layers.length > 0 && (
                            <Space size={4} wrap>
                              {p.layers.map((layer) => (
                                <Tag key={layer} color={LAYER_COLORS[layer] ?? 'default'}>
                                  {layer}
                                </Tag>
                              ))}
                            </Space>
                          )}

                          {/* Task progress */}
                          {p.artifacts?.tasks && (
                            <Space>
                              <FileTextOutlined />
                              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                                任务进度：{p.artifacts.tasks.completed}/{p.artifacts.tasks.total}
                              </Typography.Text>
                            </Space>
                          )}

                          {/* Timestamp */}
                          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                            创建时间：{new Date(p.created).toLocaleString('zh-CN', { hour12: false })}
                          </Typography.Text>
                        </Space>
                      </Card>
                    ),
                  }
                })}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ProposalsPage
