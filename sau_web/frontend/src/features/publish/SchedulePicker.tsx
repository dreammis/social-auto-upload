import { memo } from 'react'
import { Input, Label } from '@/components/ui/index'
import { Clock } from 'lucide-react'

export interface SchedulePickerProps {
  value: string
  onChange: (value: string) => void
  label?: string
  className?: string
}

export const SchedulePicker = memo(function SchedulePicker({
  value,
  onChange,
  label = '定时发布',
  className,
}: SchedulePickerProps) {
  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-2">
        <Clock className="h-4 w-4 text-muted-foreground" />
        <Label>{label}</Label>
      </div>
      <Input
        type="datetime-local"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
})
