import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Divider,
  Form,
  Input,
  type InputRef,
  message,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  Upload,
} from 'antd'
import {
  BookOutlined,
  CloseOutlined,
  CustomerServiceOutlined,
  FileAddOutlined,
  FlagOutlined,
  FontSizeOutlined,
  InboxOutlined,
  LinkOutlined,
  NotificationOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  ReadOutlined,
  SendOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import { NOTE_PLATFORMS, PLATFORMS, api } from '../api/client'
import { useAccounts } from '../hooks/useTasks'
import { usePublishStore } from '../stores/publishStore'

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  douyin: <CustomerServiceOutlined />,
  kuaishou: <ThunderboltOutlined />,
  xiaohongshu: <BookOutlined />,
  tencent: <NotificationOutlined />,
  bilibili: <PlayCircleOutlined />,
  tiktok: <VideoCameraOutlined />,
  baijiahao: <ReadOutlined />,
}

const PLATFORMS_WITH_ICONS = PLATFORMS.map((p) => ({
  ...p,
  icon: PLATFORM_ICONS[p.value] ?? undefined,
})) as typeof PLATFORMS

const BILIBILI_TIDS = [
  { id: 1, name: '动画' },
  { id: 13, name: '番剧' },
  { id: 168, name: '国创' },
  { id: 3, name: '音乐' },
  { id: 129, name: '舞蹈' },
  { id: 4, name: '游戏' },
  { id: 17, name: '单机游戏' },
  { id: 36, name: '科技' },
  { id: 188, name: '数码' },
  { id: 234, name: '美食' },
  { id: 223, name: '汽车' },
  { id: 155, name: '时尚' },
  { id: 202, name: '资讯' },
  { id: 181, name: '影视' },
  { id: 177, name: '纪录片' },
  { id: 23, name: '电影' },
  { id: 11, name: '电视剧' },
]

type PublishMode = 'video' | 'note'

type PublishForm = {
  platforms?: string[]
  accounts?: string[]
  title?: string
  desc?: string
  note?: string
  tags?: string
  schedule?: string
  headless?: boolean
  thumbnail?: string
  thumbnail_landscape?: string
  thumbnail_portrait?: string
  product_link?: string
  product_title?: string
  tid?: number
  short_title?: string
  category?: string
  is_draft?: boolean
}

function parseAccountKey(key: string) {
  const parts = key.split('::')
  return parts[1] ?? key
}

function formatTaskId(value?: string) {
  if (!value) return '-'
  return value.length > 14 ? `...${value.slice(-10)}` : value
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function SectionHeader({ icon, title, color }: { icon: React.ReactNode; title: string; color?: string }) {
  return (
    <div className="publish-section-header">
      <div
        className="section-icon"
        style={{ background: color ? `${color}12` : 'rgba(22,119,255,0.08)', color: color ?? '#1677ff' }}
      >
        {icon}
      </div>
      <span className="section-title">{title}</span>
    </div>
  )
}

function PublishPage() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [videoForm] = Form.useForm<PublishForm>()
  const [noteForm] = Form.useForm<PublishForm>()

  const videoTitleRef = useRef<InputRef | null>(null)
  const noteTitleRef = useRef<InputRef | null>(null)
  const videoFileRef = useRef<File | null>(null)
  const [videoFileInfo, setVideoFileInfo] = useState<{ name: string; size: number } | null>(null)
  const [noteImageFiles, setNoteImageFiles] = useState<File[]>([])
  const navigateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: accountOptions = [], refetch: refetchAccounts } = useAccounts()
  const lastTaskIds = usePublishStore((s) => s.lastTaskIds)
  const submitSuccess = usePublishStore((s) => s.submitSuccess)
  const setLastTaskIds = usePublishStore((s) => s.setLastTaskIds)
  const setSubmitSuccess = usePublishStore((s) => s.setSubmitSuccess)

  const submitVideoForm = async (values: PublishForm) => {
    setSubmitting(true)
    try {
      const platforms = values.platforms ?? []
      const accountKeys = values.accounts ?? []
      if (!platforms.length || !accountKeys.length) {
        message.warning('请选择平台和账号')
        return
      }
      if (!videoFileRef.current) {
        message.warning('请选择视频文件')
        return
      }

      const tasks = platforms.flatMap((platform) =>
        accountKeys.map((accountKey) =>
          api
            .uploadVideo({
              platform,
              account: parseAccountKey(accountKey),
              title: values.title ?? '',
              file: videoFileRef.current!,
              desc: values.desc,
              tags: values.tags,
              schedule: values.schedule || undefined,
              headless: values.headless ? 'true' : 'false',
              thumbnail: values.thumbnail || undefined,
              thumbnail_landscape: values.thumbnail_landscape || undefined,
              thumbnail_portrait: values.thumbnail_portrait || undefined,
              product_link: values.product_link || undefined,
              product_title: values.product_title || undefined,
              tid: values.tid || undefined,
              short_title: values.short_title || undefined,
              category: values.category || undefined,
              is_draft: values.is_draft ? 'true' : undefined,
            })
            .then((res) => ({ platform, accountKey, success: res.success, taskId: res.data?.task_id })),
        ),
      )

      const results = await Promise.all(tasks)
      const ids: string[] = []
      results.forEach((item) => {
        if (item.success && item.taskId) ids.push(item.taskId)
      })
      setLastTaskIds(ids)

      const failed = results.filter((item) => !item.success)
      if (failed.length) {
        message.error(`有 ${failed.length} 个任务提交失败`)
      } else {
        message.success(`已提交 ${results.length} 个视频上传任务`)
      }
      videoForm.resetFields()
      setVideoFileInfo(null)
      videoFileRef.current = null
      videoTitleRef.current?.focus()
      setSubmitSuccess({ count: results.length, mode: '视频', taskIds: ids })
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
      navigateTimerRef.current = setTimeout(() => navigate('/tasks'), 1500)
    } catch {
      message.error('视频请求失败，请检查后端连接')
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    return () => {
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
    }
  }, [])

  const submitNoteForm = async (values: PublishForm) => {
    setSubmitting(true)
    try {
      const platforms = values.platforms ?? []
      const accountKeys = values.accounts ?? []
      if (!platforms.length || !accountKeys.length) {
        message.warning('请选择平台和账号')
        return
      }
      if (noteImageFiles.length === 0) {
        message.warning('请至少添加一张图片')
        return
      }

      const tasks = platforms.flatMap((platform) =>
        accountKeys.map((accountKey) =>
          api
            .uploadNoteMultipart({
              platform,
              account: parseAccountKey(accountKey),
              title: values.title ?? '',
              note: values.note,
              tags: values.tags,
              schedule: values.schedule || undefined,
              headless: values.headless ? 'true' : 'false',
              images: noteImageFiles,
            })
            .then((res) => ({ platform, accountKey, success: res.success, taskId: res.data?.task_id })),
        ),
      )

      const results = await Promise.all(tasks)
      const ids: string[] = []
      results.forEach((item) => {
        if (item.success && item.taskId) ids.push(item.taskId)
      })
      setLastTaskIds(ids)

      const failed = results.filter((item) => !item.success)
      if (failed.length) {
        message.error(`有 ${failed.length} 个任务提交失败`)
      } else {
        message.success(`已提交 ${results.length} 个图文上传任务`)
      }
      noteForm.resetFields()
      setNoteImageFiles([])
      noteTitleRef.current?.focus()
      setSubmitSuccess({ count: results.length, mode: '图文', taskIds: ids })
      if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
      navigateTimerRef.current = setTimeout(() => navigate('/tasks'), 1500)
    } catch {
      message.error('图文请求失败，请检查后端连接')
    } finally {
      setSubmitting(false)
    }
  }

  const renderCommonFields = (mode: PublishMode) => (
    <>
      <div className="publish-section">
        <SectionHeader icon={<SendOutlined />} title="发布目标" color="#1677ff" />
        <Row gutter={16}>
          <Col xs={24} lg={12}>
            <Form.Item
              name="platforms"
              label="发布平台"
              rules={[{ required: true, message: '请选择平台' }]}
              className="publish-form-item"
            >
              <Select
                mode="multiple"
                allowClear
                maxTagCount="responsive"
                placeholder="选择发布平台"
                size="large"
              >
                {(mode === 'note' ? NOTE_PLATFORMS : PLATFORMS_WITH_ICONS).map((p) => (
                  <Select.Option key={p.value} value={p.value} label={p.label}>
                    <Space>
                      {p.icon}
                      <span>{p.label}</span>
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} lg={12}>
            <Form.Item
              name="accounts"
              label="发布账号"
              rules={[{ required: true, message: '请选择账号' }]}
              className="publish-form-item"
            >
              <Select
                mode="multiple"
                allowClear
                maxTagCount="responsive"
                placeholder="选择发布账号"
                size="large"
              >
                {accountOptions.map((item) => (
                  <Select.Option
                    key={`${item.platform}_${item.account_name}`}
                    value={`${item.platform}::${item.account_name}`}
                  >
                    {item.platform} / {item.account_name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>
      </div>

      <div className="publish-section">
        <SectionHeader icon={<FileAddOutlined />} title="内容素材" color="#7c3aed" />

        {mode === 'video' && (
          <Form.Item
            label="视频文件"
            rules={[{ required: true, message: '请选择视频文件' }]}
            className="publish-form-item"
          >
            <Upload.Dragger
              multiple={false}
              accept="video/*"
              showUploadList={false}
              className="publish-upload-area"
              beforeUpload={(file) => {
                videoFileRef.current = file
                setVideoFileInfo({ name: file.name, size: file.size })
                return false
              }}
              onRemove={() => {
                videoFileRef.current = null
                setVideoFileInfo(null)
                return true
              }}
            >
              <div style={{ padding: '24px 0' }}>
                <InboxOutlined style={{ fontSize: 36, color: '#1890ff' }} />
                <div style={{ marginTop: 8, fontSize: 14, color: '#666' }}>
                  点击此区域或拖拽视频文件到此处上传
                </div>
                <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
                  支持 MP4 / MOV / AVI 等常见格式
                </div>
              </div>
            </Upload.Dragger>
          </Form.Item>
        )}

        {mode === 'video' && videoFileInfo && (
          <div className="publish-file-info">
            <div className="file-icon">
              <VideoCameraOutlined />
            </div>
            <div className="file-details">
              <div className="file-name">{videoFileInfo.name}</div>
              <div className="file-meta">{formatFileSize(videoFileInfo.size)}</div>
            </div>
          </div>
        )}

        <Form.Item
          name="title"
          label="标题"
          rules={[{ required: true, message: '请输入标题' }]}
          className="publish-form-item"
        >
          <Input
            ref={mode === 'video' ? videoTitleRef : noteTitleRef}
            size="large"
            prefix={<FontSizeOutlined style={{ color: '#bfbfbf' }} />}
            placeholder={mode === 'video' ? '请输入视频标题（建议 6-20 字）' : '请输入图文标题'}
            maxLength={100}
            showCount
          />
        </Form.Item>

        {mode === 'video' ? (
          <Form.Item name="desc" label="视频简介" className="publish-form-item">
            <Input.TextArea
              autoSize={{ minRows: 4, maxRows: 8 }}
              placeholder="补充视频简介、背景说明或发布备注"
              showCount
              maxLength={1000}
            />
          </Form.Item>
        ) : (
          <Form.Item name="note" label="图文正文" className="publish-form-item">
            <Input.TextArea
              autoSize={{ minRows: 6, maxRows: 10 }}
              placeholder="请输入图文正文，多行内容会自动换行显示"
              showCount
              maxLength={3000}
            />
          </Form.Item>
        )}

        {mode === 'note' && (
          <div className="publish-section" style={{ marginBottom: 0 }}>
            <Form.Item label="图片" className="publish-form-item">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <Upload.Dragger
                  multiple
                  accept="image/*"
                  showUploadList={false}
                  className="publish-upload-area"
                  beforeUpload={(file) => {
                    setNoteImageFiles((prev) => [...prev, file])
                    return false
                  }}
                >
                  <div style={{ padding: '16px 0' }}>
                    <PictureOutlined style={{ fontSize: 28, color: '#7c3aed' }} />
                    <div style={{ marginTop: 6, fontSize: 13, color: '#666' }}>
                      点击添加图片
                    </div>
                  </div>
                </Upload.Dragger>
                {noteImageFiles.length > 0 && (
                  <div className="publish-image-grid">
                    {noteImageFiles.map((file, idx) => (
                      <div key={`${file.name}-${idx}`} className="publish-image-thumb">
                        <img src={URL.createObjectURL(file)} alt={`图片 ${idx + 1}`} />
                        <button className="remove-btn" onClick={() => {
                          setNoteImageFiles((prev) => prev.filter((_, i) => i !== idx))
                        }} title="移除">
                          <CloseOutlined />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  支持 JPG / PNG / GIF / WebP，可添加多张
                </Typography.Text>
              </div>
            </Form.Item>
          </div>
        )}
      </div>

      <div className="publish-section">
        <SectionHeader icon={<SettingOutlined />} title="发布设置" color="#059669" />
        <Row gutter={16}>
          <Col xs={24} lg={12}>
            <Form.Item name="tags" label="标签" className="publish-form-item">
              <Select
                mode="tags"
                allowClear
                placeholder="输入标签后按 Enter"
                size="large"
              />
            </Form.Item>
          </Col>
          <Col xs={24} lg={12}>
            <Form.Item
              name="schedule"
              label="定时发布"
              className="publish-form-item"
              rules={[
                {
                  validator(_: unknown, value: string | undefined) {
                    if (!value) return Promise.resolve()
                    const selected = new Date(value)
                    const now = new Date()
                    const diffMs = selected.getTime() - now.getTime()
                    const diffHours = diffMs / (1000 * 60 * 60)
                    if (diffHours < 2) {
                      return Promise.reject(new Error('定时发布时间必须大于当前时间 2 小时'))
                    }
                    return Promise.resolve()
                  },
                },
              ]}
            >
              <Input
                type="datetime-local"
                size="large"
                className="publish-date-input"
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={16}>
          <Col xs={24} lg={12}>
            <Form.Item name="headless" label="浏览器模式" className="publish-form-item" valuePropName="checked">
              <Checkbox>无头模式（不显示浏览器窗口）</Checkbox>
            </Form.Item>
          </Col>
        </Row>

        {mode === 'video' && (
          <Row gutter={16}>
            <Col xs={24} lg={12}>
              <Form.Item name="thumbnail" label="封面地址（可选）" className="publish-form-item">
                <Input size="large" placeholder="封面图片 URL 或 Data URI" prefix={<PictureOutlined style={{ color: '#bfbfbf' }} />} />
              </Form.Item>
            </Col>
          </Row>
        )}
      </div>

      {mode === 'video' && (
        <div className="publish-section" style={{ marginBottom: 0 }}>
          <SectionHeader icon={<SettingOutlined />} title="高级选项" color="#d97706" />
          <Row gutter={16}>
            <Col xs={24} lg={12}>
              <Form.Item name="thumbnail_landscape" label="横版封面（可选，4:3）" className="publish-form-item">
                <Input size="large" placeholder="封面图片 URL 或 Data URI" />
              </Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="thumbnail_portrait" label="竖版封面（可选，3:4）" className="publish-form-item">
                <Input size="large" placeholder="封面图片 URL 或 Data URI" />
              </Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="product_link" label="商品链接（抖音）" className="publish-form-item">
                <Input size="large" placeholder="https://" prefix={<LinkOutlined style={{ color: '#bfbfbf' }} />} />
              </Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="product_title" label="商品标题（抖音）" className="publish-form-item">
                <Input size="large" placeholder="可选商品标题" />
              </Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="tid" label="Bilibili 分类" className="publish-form-item">
                <Select size="large" allowClear placeholder="选择 Bilibili 分区">
                  {BILIBILI_TIDS.map((t) => (
                    <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="short_title" label="短标题（视频号）" className="publish-form-item">
                <Input size="large" placeholder="可选视频号短标题" />
              </Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="category" label="原创分类（视频号）" className="publish-form-item">
                <Input size="large" placeholder="可选原创内容分类" />
              </Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="is_draft" label="存为草稿（视频号）" className="publish-form-item" valuePropName="checked">
                <Checkbox>保存为草稿不发布</Checkbox>
              </Form.Item>
            </Col>
          </Row>
        </div>
      )}
    </>
  )

  const handleGoToTasks = () => {
    if (navigateTimerRef.current) clearTimeout(navigateTimerRef.current)
    navigate('/tasks')
  }

  const accountCount = accountOptions.length
  const platformCount = PLATFORMS.length

  return (
    <div style={{ padding: 0 }}>
      {submitSuccess && (
        <Alert
          type="success"
          showIcon
          closable
          onClose={() => setSubmitSuccess(null)}
          style={{ marginBottom: 16, borderRadius: 14 }}
          message={
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <span>
                <strong>{submitSuccess.count}</strong> 个{submitSuccess.mode}上传任务已提交！任务将持久化保存，重启后端也不丢失。
              </span>
              <Button type="primary" size="small" onClick={handleGoToTasks}>
                查看任务状态 →
              </Button>
            </Space>
          }
        />
      )}
      <Row gutter={24} align="top">
        <Col xs={24} xl={16}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card
              className="publish-card"
              title={
                <Space>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <VideoCameraOutlined style={{ color: '#1677ff' }} />
                    <span>发布视频</span>
                  </span>
                  <Tag color="magenta" style={{ borderRadius: 6 }}>Video</Tag>
                </Space>
              }
            >
              <Form form={videoForm} layout="vertical" onFinish={submitVideoForm} initialValues={{ headless: true }}>
                {renderCommonFields('video')}
                <Divider style={{ margin: '20px 0 16px' }} />
                <Alert
                  type="info"
                  showIcon
                  className="publish-tip"
                  message="提交后即创建视频上传任务，可在「任务列表」追踪执行状态。"
                  style={{ marginBottom: 16 }}
                />
                <Space>
                  <Button onClick={() => {
                    videoForm.resetFields()
                    setVideoFileInfo(null)
                    videoFileRef.current = null
                  }}>
                    清空
                  </Button>
                  <Button type="primary" htmlType="submit" loading={submitting} size="large">
                    提交视频
                  </Button>
                </Space>
              </Form>
            </Card>

            <Card
              className="publish-card"
              title={
                <Space>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <PictureOutlined style={{ color: '#7c3aed' }} />
                    <span>发布图文</span>
                  </span>
                  <Tag color="purple" style={{ borderRadius: 6 }}>Note</Tag>
                </Space>
              }
            >
              <Form form={noteForm} layout="vertical" onFinish={submitNoteForm} initialValues={{ headless: true }}>
                {renderCommonFields('note')}
                <Divider style={{ margin: '20px 0 16px' }} />
                <Alert
                  type="info"
                  showIcon
                  className="publish-tip"
                  message="支持拖拽上传多张图片，提交后即创建图文上传任务。"
                  style={{ marginBottom: 16 }}
                />
                <Space>
                  <Button onClick={() => { noteForm.resetFields(); setNoteImageFiles([]) }}>清空</Button>
                  <Button type="primary" htmlType="submit" loading={submitting} size="large">
                    提交图文
                  </Button>
                </Space>
              </Form>
            </Card>
          </Space>
        </Col>

        <Col xs={24} xl={8}>
          <Card
            className="publish-card publish-side-card"
            title={
              <Space>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FlagOutlined style={{ color: '#d97706' }} />
                  <span>发布概览</span>
                </span>
              </Space>
            }
            extra={
              <Button size="small" onClick={() => refetchAccounts()}>
                刷新
              </Button>
            }
          >
            <Space direction="vertical" style={{ width: '100%' }} size={0}>
              <div className="side-stat">
                <span className="side-stat-label">可用账号</span>
                <span className="side-stat-value active">{accountCount}</span>
              </div>
              <div className="side-stat">
                <span className="side-stat-label">支持平台</span>
                <span className="side-stat-value">{platformCount}</span>
              </div>
              <div className="side-stat">
                <span className="side-stat-label">最近提交</span>
                <span className="side-stat-value">{lastTaskIds.length > 0 ? `${lastTaskIds.length} 个` : '暂无'}</span>
              </div>

              <Divider style={{ margin: '8px 0' }} />

              <div style={{ padding: '4px 0' }}>
                <Typography.Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
                  最新任务 ID
                </Typography.Text>
                {lastTaskIds.length === 0 ? (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    暂无提交记录
                  </Typography.Text>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {lastTaskIds.map((id) => (
                      <Tag key={id} color="blue" style={{ fontSize: 11, borderRadius: 6 }}>
                        {formatTaskId(id)}
                      </Tag>
                    ))}
                  </div>
                )}
              </div>

              <Divider style={{ margin: '8px 0' }} />

              <div style={{ padding: '4px 0' }}>
                <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
                  后端地址：<code style={{ fontSize: 11 }}>http://localhost:5409</code>
                </Typography.Text>
                <Typography.Text type="secondary" style={{ fontSize: 11, display: 'block' }}>
                  接口：<code style={{ fontSize: 11 }}>/api/upload/*</code>
                </Typography.Text>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default PublishPage