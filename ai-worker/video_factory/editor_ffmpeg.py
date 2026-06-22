"""FFmpeg-based video editor for the AI Video Factory."""

import ffmpeg
import logging

logger = logging.getLogger(__name__)


class FFmpegEditor:
    """Wrapper around ffmpeg-python for common video operations."""

    @staticmethod
    def merge_audio_video(
        video_path: str,
        audio_path: str,
        output_path: str,
        overwrite: bool = True,
    ) -> str:
        """Merge an audio track onto a background video.

        Args:
            video_path: Path to the source video file.
            audio_path: Path to the audio file to overlay.
            output_path: Destination path for the merged output.
            overwrite: Overwrite output if it already exists.

        Returns:
            The output_path on success.

        Raises:
            ffmpeg.Error: If ffmpeg exits with a non-zero code.
        """
        logger.info(
            "Merging audio=%s into video=%s -> %s",
            audio_path,
            video_path,
            output_path,
        )

        video_input = ffmpeg.input(video_path)
        audio_input = ffmpeg.input(audio_path)

        (
            ffmpeg.output(
                video_input.video,
                audio_input.audio,
                output_path,
                vcodec="copy",
                acodec="aac",
                shortest=None,
            )
            .overwrite_output() if overwrite else
            ffmpeg.output(
                video_input.video,
                audio_input.audio,
                output_path,
                vcodec="copy",
                acodec="aac",
                shortest=None,
            )
        ).run(quiet=True)

        logger.info("Merge complete: %s", output_path)
        return output_path

    @staticmethod
    def burn_subtitles(
        video_path: str,
        subtitle_path: str,
        output_path: str,
    ) -> str:
        """Burn an SRT/ASS subtitle file into a video.

        Args:
            video_path: Source video.
            subtitle_path: Path to .srt or .ass subtitle file.
            output_path: Destination path.

        Returns:
            The output_path on success.
        """
        logger.info(
            "Burning subtitles=%s into video=%s -> %s",
            subtitle_path,
            video_path,
            output_path,
        )

        (
            ffmpeg.input(video_path)
            .output(
                output_path,
                vf=f"subtitles={subtitle_path}",
                acodec="copy",
            )
            .overwrite_output()
            .run(quiet=True)
        )

        logger.info("Subtitle burn complete: %s", output_path)
        return output_path
