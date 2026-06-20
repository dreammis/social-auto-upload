import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Col,
  Collapse,
  Descriptions,
  Drawer,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import { BorderLeftOutlined, CopyOutlined, DeleteOutlined, FileTextOutlined, LoadingOutlined, PlusOutlined, RedoOutlined } from '@ant-design/icons'
import { PLATFORMS, api, type TaskItem } from '../api/client'
import { useTasks, useTaskLogs } from '../hooks/useTasks'
import { useQueryClient } from '@tanstack/react-query'

type StatusType = 'all' | 'pending' | 'running' | 'success' | 'failed' | 'error'

const STATUS_OPTIONS: { label: string; value: StatusType }[] = [
  { label: '全部', value: 'all' },
  { label: '等待中', value: 'pending' },
  { label: '执行中', value: 'running' },
  { label: '成功', value: 'success' },
  { label: '失败', value: 'failed' },
  { label: '异常', value: 'error' },
]

const STATUS_META: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '执行中' },
  success: { color: 'success', label: '成功' },
  failed: { color: 'error', label: '失败' },
  error: { color: 'error', label: '异常' },
}

function formatDateTime(value?: string) {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', { hour12: false })
}

function shortenId(value?: string) {
  if (!value) return '-'
  if (value.length <= 16) return value
  // Smart truncation: try to keep the action prefix, drop middle of the random suffix
  const lastDash = value.lastIndexOf('-')
  if (lastDash > 0) {
    const prefix = value.slice(0, lastDash)      // e.g. "upload-video"
    const suffix = value.slice(lastDash + 1)       // e.g. "292beaaec7ef"
    const short = `${prefix}-${suffix.slice(-6)}`  // e.g. "upload-video-aec7ef"
    return short.length <= 24 ? short : `${prefix.slice(0, 10)}-${suffix.slice(-6)}`
  }
  return `${value.slice(0, 8)}...${value.slice(-6)}`
}

function TaskDrawerContent({ task }: { task: TaskItem }) {
  const { data: taskLogs = [], isLoading: logsLoading } = useTaskLogs(task.task_id, task.status)
  const statusMeta = STATUS_META[task.status ?? 'pending'] ?? STATUS_META.pending
  const logsEndRef = useRef<HTMLDivElement | null>(null)

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [taskLogs])

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Descriptions column={1} size="small" bordered>
        <Descriptions.Item label="任务 ID">
          <Typography.Text code copyable={{ text: task.task_id }} style={{ fontSize: 12, wordBreak: 'break-all' }}>
            {task.task_id}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="平台">{task.platform || '-'}</Descriptions.Item>
        <Descriptions.Item label="动作">{task.action || '-'}</Descriptions.Item>
        <Descriptions.Item label="账号">{task.account || '-'}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color={statusMeta.color}>{statusMeta.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{formatDateTime(task.created)}</Descriptions.Item>
        <Descriptions.Item label="退出码">
          {task.code !== undefined && task.code !== null ? (
            <Tag color={task.code === 0 ? 'success' : 'error'}>{task.code}</Tag>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="错误信息">
          {task.error ? (
            <Typography.Paragraph
              code
              style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 12, maxHeight: 200, overflow: 'auto' }}
              copyable
            >
              {task.error}
            </Typography.Paragraph>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        {task.result && (() => {
          let resultData: Record<string, string>
          try { resultData = JSON.parse(task.result) } catch { return null }
          const entries = Object.entries(resultData).filter(([, v]) => v !== undefined && v !== null && v !== '')
          if (entries.length === 0) return null
          return entries.map(([key, value]) => {
            let label = key
            if (key === 'video_url') label = '视频链接'
            else if (key === 'publish_status') label = '发布状态'
            else if (key === 'verified') label = '发布验证'
            return (
              <Descriptions.Item label={label} key={key}>
                {key === 'verified' ? (
                  <Tag color={value === true || value === 'true' ? 'success' : 'warning'}>
                    {value === true || value === 'true' ? '已验证' : '未验证'}
                  </Tag>
                ) : key === 'video_url' && value ? (
                  <Typography.Link href={value} target="_blank" style={{ wordBreak: 'break-all' }}>
                    {value}
                  </Typography.Link>
                ) : (
                  <Typography.Text style={{ wordBreak: 'break-all' }}>{String(value)}</Typography.Text>
                )}
              </Descriptions.Item>
            )
          })
        })()}
        {task.status === 'success' && (() => {
          try {
            const resultData = task.result ? JSON.parse(task.result) : null
            if (resultData && resultData.verified === false) {
              return (
                <Descriptions.Item label="⚠️ 提示">
                  <Typography.Text type="warning">
                    视频已提交但未在内容管理页验证成功。请检查平台后台确认视频状态（可能在审核中）。
                  </Typography.Text>
                </Descriptions.Item>
              )
            }
          } catch { /* ignore */ }
          return null
        })()}
        <Descriptions.Item label="执行命令">
          {task.argv ? (
            <Typography.Paragraph
              code
              style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 12, maxHeight: 300, overflow: 'auto' }}
              copyable
            >
              {(() => {
                try {
                  return JSON.parse(task.argv).join(' ')
                } catch {
                  return task.argv
                }
              })()}
            </Typography.Paragraph>
          ) : (
            '-'
          )}
        </Descriptions.Item>
      </Descriptions>

      {/* Running logs */}
      <Collapse
        defaultActiveKey={[]}
        items={[
          {
            key: 'logs',
            label: (
              <Space>
                <FileTextOutlined />
                <Typography.Text strong>运行日志</Typography.Text>
                <Tag>{taskLogs.length} 条</Tag>
                {(task.status === 'pending' || task.status === 'running') && (
                  <LoadingOutlined style={{ color: '#1890ff' }} />
                )}
                {taskLogs.length > 0 && (
                  <Tooltip title="复制全部日志">
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={async (e) => {
                        e.stopPropagation()
                        const text = taskLogs.map(e => `[${e.ts}] ${e.message}`).join('\n')
                        await navigator.clipboard.writeText(text)
                        message.success('日志已复制到剪贴板')
                      }}
                    />
                  </Tooltip>
                )}
              </Space>
            ),
            children: (
              <div
                style={{
                  background: '#1e1e1e',
                  color: '#d4d4d4',
                  borderRadius: 6,
                  padding: '8px 12px',
                  maxHeight: 400,
                  overflow: 'auto',
                  fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
                  fontSize: 12,
                  lineHeight: 1.6,
                }}
              >
                {logsLoading ? (
                  <Typography.Text type="secondary" style={{ color: '#888' }}>
                    加载中...
                  </Typography.Text>
                ) : taskLogs.length === 0 ? (
                  <Typography.Text type="secondary" style={{ color: '#888' }}>
                    暂无日志
                  </Typography.Text>
                ) : (
                  <>
                    {taskLogs.map((entry, idx) => (
                      <div key={idx} style={{ marginBottom: 2 }}>
                        <span style={{ color: '#6a9955', marginRight: 8 }}>{entry.ts}</span>
                        <span>{entry.message}</span>
                      </div>
                    ))}
                    <div ref={logsEndRef} />
                  </>
                )}
              </div>
            ),
          },
        ]}
      />
    </Space>
  )
}


function TasksPage() {
  const qc = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState<StatusType>('all')
  const [drawerTask, setDrawerTask] = useState<TaskItem | null>(null)
  const [retrying, setRetrying] = useState<string | null>(null)
  const [manualRefreshing, setManualRefreshing] = useState(false)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [addForm] = Form.useForm()

  // TanStack Query: auto-polls every 3s
  const { data: tasks = [], isLoading, refetch } = useTasks()

  const filteredData = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return tasks
      .filter((item) => {
        if (status !== 'all' && (item.status ?? '') !== status) return false
        if (!kw) return true
        return (
          (item.task_id ?? '').toLowerCase().includes(kw) ||
          (item.platform ?? '').toLowerCase().includes(kw) ||
          (item.action ?? '').toLowerCase().includes(kw) ||
          (item.account ?? '').toLowerCase().includes(kw)
        )
      })
      .sort((a, b) => (b.created ?? '').localeCompare(a.created ?? ''))
  }, [tasks, keyword, status])

  const counts = useMemo(() => {
    const map: Record<string, number> = { all: 0 }
    tasks.forEach((item) => {
      map.all += 1
      map[item.status ?? 'pending'] = (map[item.status ?? 'pending'] || 0) + 1
    })
    return map
  }, [tasks])

  const handleRetry = useCallback(async (record: TaskItem) => {
    setRetrying(record.task_id)
    try {
      const res = await api.retryTask(record.task_id)
      if (res.success && res.data?.task_id) {
        message.success(`已创建重试任务：${shortenId(res.data.task_id)}`)
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        message.error(res.message ?? '重试失败')
      }
    } catch {
      message.error('重试请求失败，请检查后端连接')
    } finally {
      setRetrying(null)
    }
  }, [qc])

  const handleDelete = useCallback(async (taskId: string) => {
    try {
      const res = await api.deleteTask(taskId)
      if (res.success) {
        message.success('任务已删除')
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        message.error(res.message ?? '删除失败')
      }
    } catch {
      message.error('删除请求失败')
    }
  }, [qc])

  const handleClear = useCallback(async () => {
    try {
      const res = await api.clearTasks(['success', 'failed', 'error'])
      if (res.success && res.data) {
        message.success(`已清理 ${res.data.deleted} 个任务`)
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        message.error('清理失败')
      }
    } catch {
      message.error('清理请求失败')
    }
  }, [qc])

  const handleAddTask = useCallback(async (values: { platform: string; action: string; account: string; title?: string }) => {
    try {
      const res = await api.addTask({
        platform: values.platform,
        action: values.action,
        account: values.account,
        title: values.title || undefined,
      })
      if (res.success && res.data) {
        message.success(`任务已创建：${shortenId(res.data.task_id)}`)
        setAddModalOpen(false)
        addForm.resetFields()
        qc.invalidateQueries({ queryKey: ['tasks'] })
      } else {
        message.error(res.message || '创建失败')
      }
    } catch {
      message.error('创建请求失败')
    }
  }, [qc, addForm])

  const canDelete = (status?: string) => status === 'success' || status === 'failed' || status === 'error'

  const handleOpenDrawer = useCallback((record: TaskItem) => {
    setDrawerTask(record)
  }, [])

  const handleCloseDrawer = useCallback(() => {
    setDrawerTask(null)
  }, [])

  const canRetry = (status?: string) => status === 'failed' || status === 'error'

  const columns = [
    {
      title: '任务 ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 220,
      render: (value: string) => (
        <Tooltip title={value}>
          <Typography.Text code copyable={{ text: value }}>
            {shortenId(value)}
          </Typography.Text>
        </Tooltip>
      ),
    },
    { title: '平台', dataIndex: 'platform', key: 'platform', width: 110 },
    { title: '动作', dataIndex: 'action', key: 'action', width: 140 },
    { title: '账号', dataIndex: 'account', key: 'account', width: 140 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      filters: STATUS_OPTIONS.filter((item) => item.value !== 'all').map((item) => ({ text: item.label, value: item.value })),
      onFilter: (value: React.Key | boolean, record: TaskItem) => (value as string) === (record.status ?? 'pending'),
      render: (value: string) => {
        const meta = STATUS_META[value] ?? STATUS_META.pending
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created',
      key: 'created',
      width: 180,
      sorter: (a: TaskItem, b: TaskItem) => (a.created ?? '').localeCompare(b.created ?? ''),
      render: (value: string) => <span style={{ whiteSpace: 'nowrap' }}>{formatDateTime(value)}</span>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      fixed: 'right' as const,          render: (_: unknown, record: TaskItem) => (
            <Space size="small" onClick={(e) => { e.stopPropagation() }}>
              <Button type="link" size="small" onClick={(e) => { e.stopPropagation(); handleOpenDrawer(record) }}>
                详情
              </Button>
              <Tooltip title="重新执行此任务">
                <Button
                  type="link"
                  size="small"
                  disabled={!canRetry(record.status)}
                  loading={retrying === record.task_id}
                  icon={<RedoOutlined />}
                  onClick={(e) => { e.stopPropagation(); handleRetry(record) }}
                >
                  重试
                </Button>
              </Tooltip>
              {canDelete(record.status) && (
                <Popconfirm
                  title="确认删除此任务？"
                  onConfirm={(e) => { e?.stopPropagation?.(); handleDelete(record.task_id) }}
                  onCancel={(e) => { e?.stopPropagation?.() }}
                  okText="删除"
                  cancelText="取消"
                >
                  <Tooltip title="删除任务">
                    <Button
                      type="link"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(e) => { e.stopPropagation() }}
                    />
                  </Tooltip>
                </Popconfirm>
              )}
            </Space>
          ),
    },
  ]

  const drawerStatusMeta = drawerTask ? STATUS_META[drawerTask.status ?? 'pending'] ?? STATUS_META.pending : null

  // ---- Resizable drawer (direct DOM, kill transitions during drag) ----
  const [drawerWidth, setDrawerWidth] = useState(520)
  const drawerElRef = useRef<HTMLElement | null>(null)
  const origTransitionRef = useRef('')
  const resizeCleanupRef = useRef<(() => void) | null>(null)

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startW = drawerWidth

    // Find the Drawer's content wrapper (Ant Design renders via portal)
    const wrapper = document.querySelector('.ant-drawer-content-wrapper') as HTMLElement | null
    drawerElRef.current = wrapper
    const handleEl = e.currentTarget as HTMLElement

    // Kill CSS transition on the drawer so width changes are instant
    origTransitionRef.current = wrapper?.style.transition ?? ''
    if (wrapper) wrapper.style.transition = 'none'

    const handleMouseMove = (ev: MouseEvent) => {
      const delta = startX - ev.clientX
      const next = Math.min(Math.max(360, startW + delta), 960)

      if (drawerElRef.current) {
        drawerElRef.current.style.width = next + 'px'
      }
      handleEl.style.right = next + 'px'
    }

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      resizeCleanupRef.current = null

      // Restore CSS transition
      if (drawerElRef.current) {
        drawerElRef.current.style.transition = origTransitionRef.current
      }

      // Sync final width to React state (one render)
      const final = drawerElRef.current
        ? parseInt(drawerElRef.current.style.width, 10)
        : startW
      setDrawerWidth(final)
      drawerElRef.current = null
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    resizeCleanupRef.current = () => {
      if (drawerElRef.current) {
        drawerElRef.current.style.transition = origTransitionRef.current
      }
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      drawerElRef.current = null
    }
  }, [drawerWidth])

  // Clean up resize listeners on unmount
  useEffect(() => {
    return () => {
      resizeCleanupRef.current?.()
    }
  }, [])

  return (
    <div style={{ padding: 0 }}>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="全部任务" value={counts.all} prefix={<Badge status="default" />} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="执行中" value={counts.running ?? 0} prefix={<Badge status="processing" />} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="成功"
              value={counts.success ?? 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<Badge status="success" />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="失败 / 异常"
              value={(counts.failed ?? 0) + (counts.error ?? 0)}
              valueStyle={{ color: '#cf1322' }}
              prefix={<Badge status="error" />}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Row gutter={12} align="middle" style={{ marginBottom: 12 }}>
          <Col xs={24} sm={12} md={10}>
            <Input.Search
              placeholder="搜索任务 ID、平台、账号"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onSearch={(value) => setKeyword(value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select<StatusType>
              value={status}
              onChange={(val) => setStatus(val)}
              options={STATUS_OPTIONS}
              style={{ width: '100%' }}
            />
          </Col>
          <Col xs={24} sm={24} md={8} style={{ textAlign: 'right' }}>
            <Space size="small" style={{ marginLeft: 'auto' }}>
              <Popconfirm
                title="清理所有已完成、失败、异常的任务？"
                onConfirm={handleClear}
                okText="清理"
                cancelText="取消"
              >
                <Button icon={<DeleteOutlined />}>
                  清理
                </Button>
              </Popconfirm>
              <Button
                icon={<PlusOutlined />}
                onClick={() => setAddModalOpen(true)}
              >
                新建任务
              </Button>
              <Button
                onClick={async () => {
                  setManualRefreshing(true)
                  await refetch()
                  setManualRefreshing(false)
                }}
                loading={manualRefreshing}
              >
                刷新
              </Button>
              <Tooltip title="每 3 秒自动刷新">
                <Badge
                  status="processing"
                  text={
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      TanStack Query 轮询中
                    </Typography.Text>
                  }
                />
              </Tooltip>
            </Space>
          </Col>
        </Row>

        <Table<TaskItem>
          rowKey={(record) => record.task_id}
          loading={isLoading}
          dataSource={filteredData}
          pagination={{
            showSizeChanger: true,
            defaultPageSize: 10,
            showTotal: (total) => `共 ${total} 条`,
          }}
          size="small"
          scroll={{ x: 900 }}
          columns={columns}
          onRow={(record) => ({
            style: { cursor: 'pointer' },
            onClick: () => handleOpenDrawer(record),
          })}
        />
      </Card>

      {/* Task Detail Drawer — resizable */}
      {drawerTask && (
        <div
          onMouseDown={handleResizeStart}
          style={{
            position: 'fixed',
            top: 0,
            bottom: 0,
            // Position handle at the left edge of the Drawer
            right: drawerWidth,
            width: 6,
            zIndex: 1050,
            cursor: 'col-resize',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'background-color 0.15s ease',
          }}
          className="drawer-resize-handle"
        >
          <BorderLeftOutlined style={{ fontSize: 10, color: '#888', opacity: 0.6 }} />
        </div>
      )}
      <Drawer
        title={
          drawerTask ? (
            <Space>
              <span>任务详情</span>
              {drawerStatusMeta && <Tag color={drawerStatusMeta.color}>{drawerStatusMeta.label}</Tag>}
            </Space>
          ) : (
            '任务详情'
          )
        }
        placement="right"
        width={drawerWidth}
        open={!!drawerTask}
        onClose={handleCloseDrawer}
        extra={
          drawerTask && canRetry(drawerTask.status) ? (
            <Button
              type="primary"
              icon={<RedoOutlined />}
              loading={retrying === drawerTask.task_id}
              onClick={() => {
                const task = drawerTask
                handleCloseDrawer()
                handleRetry(task)
              }}
            >
              重试此任务
            </Button>
          ) : undefined
        }
      >
        {drawerTask && <TaskDrawerContent task={drawerTask} />}
      </Drawer>

      <Modal
        title="新建任务"
        open={addModalOpen}
        onCancel={() => { setAddModalOpen(false); addForm.resetFields() }}
        onOk={() => addForm.submit()}
      >
        <Form form={addForm} layout="vertical" onFinish={handleAddTask}>
          <Form.Item name="platform" label="平台" rules={[{ required: true, message: '请选择平台' }]}>
            <Select placeholder="选择平台">
              {PLATFORMS.map((p) => (
                <Select.Option key={p.value} value={p.value}>{p.label}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="action" label="操作" rules={[{ required: true, message: '请选择操作' }]}>
            <Select placeholder="选择操作">
              <Select.Option value="login">登录</Select.Option>
              <Select.Option value="check">检查</Select.Option>
              <Select.Option value="upload-video">上传视频</Select.Option>
              <Select.Option value="upload-note">上传图文</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="account" label="账号" rules={[{ required: true, message: '请输入账号' }]}>
            <Input placeholder="输入账号名称" />
          </Form.Item>
          <Form.Item name="title" label="标题">
            <Input placeholder="输入标题（上传操作需要）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TasksPage
