import type { AccountItem, TaskItem } from '@/api/client'

export const sampleAccounts: AccountItem[] = [
  {
    platform: 'douyin',
    account_name: '主号',
    path: '/cookies/douyin-main.json',
  },
  {
    platform: 'xiaohongshu',
    account_name: '副号',
    path: '/cookies/xhs-secondary.json',
  },
  {
    platform: 'bilibili',
    account_name: '频道',
    path: '/cookies/bili-channel.json',
  },
]

export function makeTask(overrides: Partial<TaskItem> = {}): TaskItem {
  return {
    task_id: 'task-' + Math.random().toString(36).slice(2, 10),
    platform: 'douyin',
    action: 'upload-video',
    account: '主号',
    status: 'pending',
    created: '2024-01-01T00:00:00Z',
    code: null,
    error: null,
    argv: '["sau","douyin","upload-video","--account","主号"]',
    result: null,
    publish_detail: null,
    ...overrides,
  }
}
