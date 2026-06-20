import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, Card, Col, Form, Image, Input, Modal, message, Popconfirm, Row, Select, Space, Spin, Table, Tag, Tooltip, Typography } from 'antd'
import { CheckCircleOutlined, CheckOutlined, DeleteOutlined, QuestionCircleOutlined, ScanOutlined } from '@ant-design/icons'
import { PLATFORMS, api, type AccountItem } from '../api/client'

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:5409'

type QuickResult = {
  valid: boolean
  reason: string
  age_hours: number | null
  file_size: number | null
}

type LoginForm = {
  platform: string
  account: string
  headless: boolean
}

const QUICK_STATUS_META: Record<string, { color: string; label: string }> = {
  fresh: { color: 'success', label: '有效' },
  stale: { color: 'warning', label: '可能过期' },
  no_file: { color: 'error', label: '无文件' },
  empty: { color: 'error', label: '空文件' },
  empty_cookies: { color: 'error', label: '无Cookie' },
  verified: { color: 'success', label: '已验证' },
  invalid: { color: 'error', label: '已失效' },
}

function AccountsPage() {
  const [accounts, setAccounts] = useState<AccountItem[]>([])
  const [quickResults, setQuickResults] = useState<Map<string, QuickResult>>(new Map())
  const [loading, setLoading] = useState(false)
  const [loginSubmitting, setLoginSubmitting] = useState(false)
  const [checkingAccounts, setCheckingAccounts] = useState<Set<string>>(new Set())
  const [checkingAll, setCheckingAll] = useState(false)
  const [form] = Form.useForm<LoginForm>()
  const [qrcodeModalVisible, setQrcodeModalVisible] = useState(false)
  const [qrcodeUrl, setQrcodeUrl] = useState<string | null>(null)
  const [loginStatus, setLoginStatus] = useState<string>('')
  
  const pendingTasksRef = useRef<Map<string, string>>(new Map())
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const pollPendingTasks = useCallback(async () => {
    const pending = pendingTasksRef.current
    if (pending.size === 0) {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      return
    }

    try {
      const res = await api.getTasks()
      if (!res.success || !res.data) return

      for (const task of res.data) {
        const taskKey = Array.from(pending.entries()).find(([_, tid]) => tid === task.task_id)?.[0]
        if (!taskKey) continue

        if (task.status === 'success') {
          pending.delete(taskKey)
          setQuickResults((prev) => new Map(prev).set(taskKey, { valid: true, reason: 'verified', age_hours: null, file_size: null }))
          message.success(`深度检查通过：${taskKey}`)
        } else if (task.status === 'failed' || task.status === 'error') {
          pending.delete(taskKey)
          setQuickResults((prev) => new Map(prev).set(taskKey, { valid: false, reason: 'invalid', age_hours: null, file_size: null }))
          message.error(`深度检查失败：${taskKey}`)
        }
      }

      pendingTasksRef.current = pending
      if (pending.size === 0 && pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    } catch {
      void 0
    }
  }, [])

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
      eventSourceRef.current?.close()
    }
  }, [])

  const handleDelete = async (platform: string, account: string) => {
    try {
      const res = await api.deleteAccount(platform, account)
      if (res.success) {
        message.success(res.message || `已删除 ${platform}/${account}`)
        loadAccounts()
      } else {
        message.error(res.message || '删除失败')
      }
    } catch {
      message.error('删除请求失败')
    }
  }

  const handleCheck = async (platform: string, account: string) => {
    const key = `${platform}_${account}`
    setCheckingAccounts((prev) => new Set(prev).add(key))
    try {
      const res = await api.checkAccount(platform, account, true)
      if (res.success && res.data) {
        if (res.data.quick) {
          setQuickResults((prev) => new Map(prev).set(key, res.data!.quick))
        }
        if (res.data.task_id) {
          pendingTasksRef.current.set(key, res.data.task_id)
          message.info(`深度检查中...`)
          if (!pollTimerRef.current) {
            pollTimerRef.current = setInterval(pollPendingTasks, 2000)
          }
        }
      } else {
        message.error(res.message || '检查失败')
      }
    } catch {
      message.error('检查请求失败')
    } finally {
      setCheckingAccounts((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  const handleCheckAll = async () => {
    setCheckingAll(true)
    try {
      const res = await api.checkAllAccounts()
      if (res.success && res.data) {
        const newMap = new Map<string, QuickResult>()
        for (const item of res.data) {
          const key = `${item.platform}_${item.account}`
          newMap.set(key, item.quick)
        }
        setQuickResults(newMap)
        message.success(`已检查 ${res.data.length} 个账号`)
      } else {
        message.error('批量检查失败')
      }
    } catch {
      message.error('批量检查请求失败')
    } finally {
      setCheckingAll(false)
    }
  }

  const loadAccounts = async () => {
    setLoading(true)
    try {
      const res = await api.getAccounts()
      setAccounts(res.data)
    } catch {
      message.error('加载账号列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  const onLogin = async (values: LoginForm) => {
    setLoginSubmitting(true)
    setQrcodeModalVisible(true)
    setQrcodeUrl(null)
    setLoginStatus('正在启动浏览器...')

    const platform = values.platform
    const account = values.account
    const headless = values.headless ? 'true' : 'false'

    const qrLoginPlatforms = ['douyin', 'kuaishou', 'xiaohongshu', 'tencent']

    // For platforms without QR-code callback support (tiktok, baijiahao),
    // fall back to the original task-based login
    if (!qrLoginPlatforms.includes(platform)) {
      setQrcodeModalVisible(false)
      try {
        const data = await api.loginAccount({
          platform,
          account,
          headless: values.headless,
        })
        if (data.success) {
          message.success(`登录任务已提交：${data.data?.task_id ?? '-'}`)
          form.resetFields()
          loadAccounts()
        } else {
          message.error(data.message || '登录失败')
        }
      } catch {
        message.error('登录请求失败')
      } finally {
        setLoginSubmitting(false)
      }
      return
    }

    const eventSource = new EventSource(
      `${BASE_URL}/api/accounts/login/sse?platform=${encodeURIComponent(platform)}&account=${encodeURIComponent(account)}&headless=${encodeURIComponent(headless)}`
    )

    let connected = false

    eventSource.onopen = () => {
      connected = true
      setLoginStatus('正在连接登录服务...')
    }

    eventSource.addEventListener('qrcode', (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.image_data_url) {
          setQrcodeUrl(data.image_data_url)
          setLoginStatus('请使用手机扫码登录')
        }
      } catch {
        void 0
      }
    })

    eventSource.addEventListener('result', (e) => {
      eventSource.close()
      try {
        const data = JSON.parse(e.data)
        if (data.success) {
          setLoginStatus('登录成功！')
          message.success('扫码登录成功')
          setTimeout(() => {
            setQrcodeModalVisible(false)
            form.resetFields()
            loadAccounts()
          }, 1000)
        } else {
          setQrcodeModalVisible(false)
          message.error(data.message || '登录失败')
          setLoginSubmitting(false)
        }
      } catch {
        setQrcodeModalVisible(false)
        message.error('登录失败，请稍后重试')
        setLoginSubmitting(false)
      }
    })

    // EventSource connection error — fires when the SSE connection closes
    // or the initial connection fails. Distinguish initial failure vs
    // normal stream ending, but DON'T also use addEventListener('error')
    // because that is the SAME built-in EventSource error event (not a named SSE event).
    eventSource.onerror = () => {
      if (!connected) {
        // Initial connection failed — server never responded
        eventSource.close()
        setQrcodeModalVisible(false)
        setLoginSubmitting(false)
        message.error('无法连接登录服务，请确认后端已启动')
      }
      // If connected=true and onerror fires, the SSE stream ended (server finished).
      // The 'result' event handler should have already dealt with success/failure.
      // If no result was received, it means the connection was interrupted unexpectedly.
    }

    // Store eventSource ref for cleanup
    eventSourceRef.current = eventSource
    // Safety timeout: close if login takes too long (>5 minutes)
    setTimeout(() => {
      eventSource.close()
      setQrcodeModalVisible(false)
      setLoginSubmitting(false)
      message.warning('登录超时，请重试')
    }, 300000)
  }

  const accountKey = (record: AccountItem) => `${record.platform}_${record.account_name}`
  const isChecking = (record: AccountItem) => checkingAccounts.has(accountKey(record))

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card title="账号列表">
        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col xs={24} sm={12} md={8}>
            <Select
              defaultValue=""
              style={{ width: '100%' }}
              onChange={async (value) => {
                const platform = value || undefined
                try {
                  const res = await api.getAccounts(platform)
                  setAccounts(res.data)
                } catch {
                  message.error('筛选失败')
                }
              }}
            >
              <Select.Option value="">全部平台</Select.Option>
              {PLATFORMS.map((p) => (
                <Select.Option key={p.value} value={p.value}>{p.label}</Select.Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Button type="primary" onClick={loadAccounts} block>
              刷新列表
            </Button>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Button
              icon={<CheckOutlined />}
              onClick={handleCheckAll}
              loading={checkingAll}
              disabled={accounts.length === 0}
              block
            >
              批量检查
            </Button>
          </Col>
        </Row>
        <Table<AccountItem>
          rowKey={(record) => `${record.platform}_${record.account_name}`}
          loading={loading}
          dataSource={accounts}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: 600 }}
          columns={[
            { title: '平台', dataIndex: 'platform', width: 100 },
            { title: '账号', dataIndex: 'account_name', width: 160 },
            {
              title: '状态',
              width: 120,
              render: (_: unknown, record: AccountItem) => {
                const key = `${record.platform}_${record.account_name}`
                const isDeepChecking = pendingTasksRef.current.has(key)
                
                if (isDeepChecking) {
                  return (
                    <Tag icon={<QuestionCircleOutlined />} color="processing">
                      验证中
                    </Tag>
                  )
                }
                
                const result = quickResults.get(key)
                if (!result) {
                  return (
                    <Tag icon={<QuestionCircleOutlined />} color="default">
                      未检查
                    </Tag>
                  )
                }
                
                const meta = QUICK_STATUS_META[result.reason] || { color: 'default', label: result.reason }
                const tooltip = result.age_hours !== null
                  ? `${meta.label} (${Math.round(result.age_hours)}小时前更新)`
                  : meta.label
                return (
                  <Tooltip title={tooltip}>
                    <Tag color={meta.color}>{meta.label}</Tag>
                  </Tooltip>
                )
              },
            },
            {
              title: '操作',
              key: 'actions',
              width: 200,
              render: (_: unknown, record: AccountItem) => (
                <Space size="small">
                  <Tooltip title="检查 Cookie 是否有效">
                    <Button
                      type="link"
                      size="small"
                      icon={<CheckCircleOutlined />}
                      loading={isChecking(record)}
                      onClick={() => handleCheck(record.platform, record.account_name)}
                    >
                      检查
                    </Button>
                  </Tooltip>
                  <Popconfirm
                    title={`确认删除 ${record.platform}/${record.account_name}？`}
                    description="删除后 Cookie 文件将被移除，无法恢复"
                    onConfirm={() => handleDelete(record.platform, record.account_name)}
                    okText="确认删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                  >
                    <Button type="link" danger size="small" icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Card title="登录账号">
        <Form form={form} layout="vertical" onFinish={onLogin} initialValues={{ platform: 'douyin', headless: true }}>
          <Row gutter={12}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item name="platform" label="平台" rules={[{ required: true, message: '请选择平台' }]}>
                <Select style={{ width: '100%' }}>
                  {PLATFORMS.map((p) => (
                    <Select.Option key={p.value} value={p.value}>{p.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item name="account" label="账号名称" rules={[{ required: true, message: '请输入账号名称' }]}>
                <Input placeholder="例如 xiandnahuang" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Form.Item name="headless" label="无头模式" initialValue={true}>
                <Select style={{ width: '100%' }}>
                  <Select.Option value={true}>是</Select.Option>
                  <Select.Option value={false}>否（显示浏览器）</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={4}>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button type="primary" htmlType="submit" loading={loginSubmitting} block>
                  登录
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      <Modal
        title={
          <Space>
            <ScanOutlined style={{ color: '#1677ff' }} />
            <span>扫码登录</span>
          </Space>
        }
        open={qrcodeModalVisible}
        footer={null}
        closable={true}
        onCancel={() => {
          setQrcodeModalVisible(false)
          setLoginSubmitting(false)
        }}
        width={380}
        centered
        maskClosable={false}
      >
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          {qrcodeUrl ? (
            <Image
              src={qrcodeUrl}
              alt="登录二维码"
              style={{ width: 240, height: 240, borderRadius: 8 }}
              preview={false}
            />
          ) : (
            <div style={{ padding: '60px 0' }}>
              <Spin size="large" />
            </div>
          )}
          <div style={{ marginTop: 16 }}>
            <Typography.Text type="secondary">
              {loginStatus || '正在获取二维码...'}
            </Typography.Text>
          </div>
        </div>
      </Modal>
    </Space>
  )
}

export default AccountsPage