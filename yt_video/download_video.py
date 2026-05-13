import yt_dlp
import subprocess
import os


def download_youtube_clip(video_name, video_id, durations):
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    temp_file = f"{video_id}_temp.mp4"

    # Download highest quality video-only stream
    # ydl_opts = {
    #     "format": "best",
    #     "outtmpl": temp_file,
    #     "quiet": True
    # }``

    # ydl_opts = {
    #     "format": "bestvideo*",
    #     "outtmpl": f"{video_id}_temp.%(ext)s",
    #     "quiet": True,
    # }

    with yt_dlp.YoutubeDL({
        "format": "bestvideo*",
        "outtmpl": f"{video_id}_temp.%(ext)s",
        "quiet": True,
    }) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        temp_file = ydl.prepare_filename(info)

    print("Downloading video...")

    # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #     ydl.download([youtube_url])

    print("Cutting clip...")

    for i,duration in enumerate(durations, 1):
        start_time = duration["start_time"]
        end_time = duration["end_time"]
        output_file = (
            f"{video_name}_{video_id}_{i}_{start_time.replace(':', '-')}_{end_time.replace(':', '-')}.mp4"
        )
        # cmd = [
        #     "ffmpeg",
        #     "-y",
        #     "-ss", start_time,
        #     "-to", end_time,
        #     "-i", temp_file ,
        #     "-c", "copy",
        #     "-an",
        #     output_file
        # ]
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", start_time,
            "-to", end_time,
            "-i", temp_file,
            "-an",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            output_file
        ]
        subprocess.run(cmd, check=True)

    # Remove temporary full video
    os.remove(temp_file)

    print(f"Saved: {output_file}")

    return output_file


# Example usage

download_youtube_clip(
    video_name = "aws_aim",
    video_id="hAk-7ImN6iM",
    durations = [
        {
            "start_time" : "01:19",
            "end_time": "02:35"
        },
        # {   
        #     "start_time" : "08:34",
        #     "end_time": "09:49"
        # },
    ]
)