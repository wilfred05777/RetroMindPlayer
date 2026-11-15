"""Generate original, tiny packaging fixtures outside the release bundle."""
from pathlib import Path
import sys
import wave
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from media_fixtures import make_video

def main():
    folder=Path(sys.argv[1]).resolve()/'fixtures'
    folder.mkdir(parents=True,exist_ok=True)
    with wave.open(str(folder/'tone.wav'),'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(8000)
        # The audible source baseline is user-confirmed; packaged tests are muted.
        out.writeframes(b'\0\0'*8000*3)
    make_video(folder/'h264-aac.mp4')
    make_video(folder/'vp9-opus.webm','libvpx-vp9','libopus')
    (folder/'metadata-unavailable.MP4').write_bytes(b'not a valid container')
    (folder/'notes.txt').write_text('Not supported media')
    print('Generated isolated media fixtures:',folder)

if __name__=='__main__':
    main()
