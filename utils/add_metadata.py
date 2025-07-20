import asyncio
import subprocess

async def set_video_metadata(input_file, output_file, width, height):
    command = [
        'ffmpeg',
        '-i', input_file,
        '-vf', f'scale={width}:{height}',
        '-c:a', 'copy',
        output_file
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        print(f"Error: {stderr.decode()}")
    else:
        print(f"Success: {stdout.decode()}")