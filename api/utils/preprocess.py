import os
from pydub import AudioSegment

def slice_audio(audio, LIMIT_SEC, UPLOAD_DIR):
    fn = audio.filename.split('.')[0]
    af = AudioSegment.from_file(audio)
    af_sec = af.duration_seconds * 1000
    print("duration(sec): {}".format(af.duration_seconds))
    # write_log("audio file length (sec): {}".format(af.duration_seconds))
    if af_sec > LIMIT_SEC:
        sho = int(af_sec / LIMIT_SEC)
        rest = af_sec % LIMIT_SEC
        split_audios = []
        for s in range(sho+1):
            splt_fn = fn + "_%d"%(s+1) + ".mp3"
            if s == 0:
                end= LIMIT_SEC
                print(":", end)
                maf = af[:end]
                maf.export(os.path.join(UPLOAD_DIR, splt_fn), format="mp3")
                split_audios.append(splt_fn)
            elif (s >= 1) and (s+1 < sho):
                stt = LIMIT_SEC * s
                end = LIMIT_SEC * (s + 1)
                print(stt, ":", end)
                maf = af[stt:end]
                maf.export(os.path.join(UPLOAD_DIR, splt_fn), format="mp3")
                split_audios.append(splt_fn)
            elif s+1 >= sho:
                stt = LIMIT_SEC * s
                print(stt, ":")
                maf = af[stt:]
                maf.export(os.path.join(UPLOAD_DIR, splt_fn), format="mp3")
                split_audios.append(splt_fn)
        return split_audios
    else:
        af.export(os.path.join(UPLOAD_DIR, audio.filename), format="mp3")
        return [audio.filename]
    
def preprocess(user,audio_file, LIMIT_SEC, UPLOAD_DIR):
    """リクエストデータを受け取り、データフレームに変換する関数"""
    # 各ファイルを取得する

    try:
        user = str(user) if user != "" else "unknown"
    except:
        user = "unknown"

    LIMIT_SEC = 5 * 60 * 1000 if q else LIMIT_SEC
    filenames = slice_audio(audio, LIMIT_SEC, UPLOAD_DIR)
    # write_log("input parameters \n ---------\n-filenames: %s\n-secret: %r\n-user: %s"%(filenames, secret, user))
    return (filenames, num, secret, q, user)