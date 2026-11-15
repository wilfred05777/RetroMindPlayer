"""Generate tiny original colour/tone clips; no downloaded media or encoders."""
from fractions import Fraction
import math
from array import array
import av


def make_video(path, video_codec='libx264', audio_codec='aac', seconds=3):
    with av.open(str(path), 'w') as out:
        video = out.add_stream(video_codec, rate=12)
        video.width, video.height = 160, 96
        video.pix_fmt = 'yuv420p'
        if video_codec == 'libx264':
            video.options = {'preset': 'ultrafast', 'crf': '30'}
        elif video_codec == 'libx265':
            video.options = {'preset': 'ultrafast', 'x265-params': 'log-level=error:pools=1'}
        elif video_codec == 'libvpx-vp9':
            video.options = {'deadline': 'realtime', 'cpu-used': '8'}
        elif video_codec == 'libsvtav1':
            video.options = {'preset': '12', 'svtav1-params': 'lp=1'}
        audio = out.add_stream(audio_codec, rate=48000) if audio_codec else None
        if audio:
            audio.layout = 'mono'
        for index in range(seconds * 12):
            frame = av.VideoFrame(160, 96, 'rgb24')
            # Distinct coloured stripes and motion make stale/black frames detectable.
            row = bytes((220, 30, 60)) * 54 + bytes((30, 200, 90)) * 53 + bytes((40, 80, 220)) * 53
            frame.planes[0].update(row * 96)
            frame.pts = index
            frame.time_base = Fraction(1, 12)
            for packet in video.encode(frame):
                out.mux(packet)
        for packet in video.encode():
            out.mux(packet)
        if audio:
            for start in range(0, seconds * 48000, 960):
                frame = av.AudioFrame(format='fltp', layout='mono', samples=960)
                samples = array('f', (.08 * math.sin(2 * math.pi * 440 * (start + i) / 48000) for i in range(960)))
                frame.planes[0].update(samples.tobytes())
                frame.sample_rate = 48000
                frame.time_base = Fraction(1, 48000)
                frame.pts = start
                for packet in audio.encode(frame):
                    out.mux(packet)
            for packet in audio.encode():
                out.mux(packet)
    return path
