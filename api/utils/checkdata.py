def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'m4a', 'mp3', 'webm', 'mp4', 'mpga', 'wav', 'mpeg', "wma"}

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_tempfile(audio_file):
    print("check")
    # ファイルが選択されているか確認
    if audio_file.filename == '':
        # 学生データが選ばれていません
        return False
    if not allowed_file(audio_file.filename):
        return False
    print("check done")
    return True