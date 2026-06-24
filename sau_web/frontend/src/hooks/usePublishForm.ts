import { useMemo, useRef, useState } from 'react'

export type PublishMode = 'video' | 'note'

export interface VideoFormState {
  platforms: string[]
  groupId: number | null
  title: string
  desc: string
  tags: string
  schedule: string
  headless: boolean
  thumbnail: string
  thumbnailLandscape: string
  thumbnailPortrait: string
  productLink: string
  productTitle: string
  tid: number | undefined
  shortTitle: string
  category: string
  isDraft: boolean
}

export interface NoteFormState {
  platforms: string[]
  groupId: number | null
  title: string
  content: string
  tags: string
  schedule: string
  headless: boolean
}

export interface ThumbnailInfo {
  name: string
  dataUri: string
}

const initialVideo: VideoFormState = {
  platforms: [],
  groupId: null,
  title: '',
  desc: '',
  tags: '',
  schedule: '',
  headless: true,
  thumbnail: '',
  thumbnailLandscape: '',
  thumbnailPortrait: '',
  productLink: '',
  productTitle: '',
  tid: undefined,
  shortTitle: '',
  category: '',
  isDraft: false,
}

const initialNote: NoteFormState = {
  platforms: [],
  groupId: null,
  title: '',
  content: '',
  tags: '',
  schedule: '',
  headless: true,
}

export function usePublishForm() {
  const [submitting, setSubmitting] = useState(false)
  const [mode, setMode] = useState<PublishMode>('video')

  const [video, setVideo] = useState<VideoFormState>(initialVideo)
  const [note, setNote] = useState<NoteFormState>(initialNote)

  const videoFileRef = useRef<File | null>(null)
  const [videoFileInfo, setVideoFileInfo] = useState<{ name: string; size: number } | null>(null)
  const [videoDragOver, setVideoDragOver] = useState(false)
  const [noteDragOver, setNoteDragOver] = useState(false)

  const [videoThumbnailInfo, setVideoThumbnailInfo] = useState<ThumbnailInfo | null>(null)
  const [videoThumbnailLandscapeInfo, setVideoThumbnailLandscapeInfo] = useState<ThumbnailInfo | null>(null)
  const [videoThumbnailPortraitInfo, setVideoThumbnailPortraitInfo] = useState<ThumbnailInfo | null>(null)

  const [noteImageFiles, setNoteImageFiles] = useState<File[]>([])
  const noteImageUrls = useMemo(
    () => noteImageFiles.map(file => URL.createObjectURL(file)),
    [noteImageFiles]
  )

  const navigateTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const updateVideo = (patch: Partial<VideoFormState>) =>
    setVideo(prev => ({ ...prev, ...patch }))

  const updateNote = (patch: Partial<NoteFormState>) =>
    setNote(prev => ({ ...prev, ...patch }))

  const resetVideo = () => {
    setVideo(initialVideo)
    videoFileRef.current = null
    setVideoFileInfo(null)
    setVideoThumbnailInfo(null)
    setVideoThumbnailLandscapeInfo(null)
    setVideoThumbnailPortraitInfo(null)
  }

  const resetNote = () => {
    setNote(initialNote)
    setNoteImageFiles([])
  }

  return {
    submitting, setSubmitting,
    mode, setMode,
    video, updateVideo, resetVideo,
    note, updateNote, resetNote,
    videoFileRef,
    videoFileInfo, setVideoFileInfo,
    videoDragOver, setVideoDragOver,
    noteDragOver, setNoteDragOver,
    videoThumbnailInfo, setVideoThumbnailInfo,
    videoThumbnailLandscapeInfo, setVideoThumbnailLandscapeInfo,
    videoThumbnailPortraitInfo, setVideoThumbnailPortraitInfo,
    noteImageFiles, setNoteImageFiles,
    noteImageUrls,
    navigateTimerRef,
  }
}
