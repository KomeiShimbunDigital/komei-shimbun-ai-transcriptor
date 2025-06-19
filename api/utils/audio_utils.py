import os
import subprocess
from pathlib import Path
from pydub import AudioSegment
from pydub.utils import mediainfo
from pydub.exceptions import CouldntDecodeError

class AudioProcessor:
    def __init__(self, output_dir: str = "processed_audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_extensions = {".m4a", ".mp3", ".webm", ".mp4", ".mpga", ".wav", ".mpeg", ".wma"}
        self.max_file_size_mb = 500

    # Ensure this method signature is exactly as follows:
    def save_original_file(self, file_content: bytes, original_filename: str, user: str) -> Path:
        """
        元の音声ファイルを指定されたユーザーのサブディレクトリに保存します。
        """
        user_dir = self.output_dir / user
        user_dir.mkdir(parents=True, exist_ok=True)
        
        file_extension = Path(original_filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            raise ValueError(f"許可されていないファイル形式です: {file_extension}")

        save_path = user_dir / original_filename
        with open(save_path, "wb") as f:
            f.write(file_content)
        return save_path

    # ... (rest of the AudioProcessor class methods)
    def validate_audio_file(self, file_path: Path) -> tuple[bool, str]:
        """
        音声ファイルの形式とサイズを検証します。
        """
        if not file_path.is_file():
            return False, "ファイルが見つかりません。"
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            return False, f"ファイルサイズが上限（{self.max_file_size_mb}MB）を超えています。"
        
        try:
            audio = AudioSegment.from_file(file_path)
            return True, "ファイルは有効です。"
        except CouldntDecodeError as e:
            # Specific error for pydub's inability to decode (often due to ffmpeg errors)
            return False, f"オーディオファイルをデコードできませんでした。ファイル形式が不正であるか、破損している可能性があります。FFmpegのエラー: {e}"
        except Exception as e:
            return False, f"不明なエラーによりファイルの検証に失敗しました: {e}"

    def get_audio_duration(self, file_path: Path) -> float:
        """
        音声ファイルの長さを秒単位で取得します。
        """
        try:
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000.0
        except Exception as e:
            raise ValueError(f"音声の長さを取得できませんでした: {e}")

    def split_audio(self, file_path: Path, segment_length: int = 600) -> list[Path]:
        """
        音声ファイルを指定された秒数で分割し、分割されたファイルのパスリストを返します。
        """
        try:
            audio = AudioSegment.from_file(file_path)
            total_length_ms = len(audio)
            segment_length_ms = segment_length * 1000
            
            split_files = []
            file_stem = file_path.stem
            file_extension = ".mp3"

            for i, start_ms in enumerate(range(0, total_length_ms, segment_length_ms)):
                end_ms = min(start_ms + segment_length_ms, total_length_ms)
                segment = audio[start_ms:end_ms]
                
                output_segment_path = self.output_dir / f"{file_stem}_part_{i:03d}{file_extension}"
                segment.export(output_segment_path, format="mp3")
                split_files.append(output_segment_path)
            
            return split_files
        except Exception as e:
            raise Exception(f"音声ファイルの分割中にエラーが発生しました: {e}")

    def convert_to_mp3_if_needed(self, file_path: Path) -> Path:
        """
        指定されたファイルがMP3でない場合、MP3に変換します。
        変換されたファイルのパスを返します。
        """
        file_extension = file_path.suffix.lower()
        if file_extension == ".mp3":
            print(f"ファイルは既にMP3形式です: {file_path}")
            return file_path
        
        output_mp3_path = file_path.with_suffix(".mp3")
        try:
            print(f"MP3に変換中: {file_path} -> {output_mp3_path}")
            audio = AudioSegment.from_file(file_path)
            audio.export(output_mp3_path, format="mp3")
            print("変換成功。元のファイルを削除します。")
            os.remove(file_path)
            return output_mp3_path
        except CouldntDecodeError as e:
            # Specific error for pydub's inability to decode during conversion
            raise Exception(f"MP3への変換中にデコードエラーが発生しました。ファイル形式が不正であるか、破損している可能性があります。FFmpegのエラー: {e}")
        except Exception as e:
            raise Exception(f"MP3への変換中に予期せぬエラーが発生しました: {e}")

    def cleanup_temp_files(self, file_paths: list[Path], keep_original: bool = False):
        """
        一時ファイルをクリーンアップします。
        """
        for f_path in file_paths:
            if f_path.is_file():
                try:
                    if keep_original and "processed_audio" in str(f_path) and not "_part_" in str(f_path):
                        continue
                    os.remove(f_path)
                    print(f"クリーンアップ: {f_path}")
                except Exception as e:
                    print(f"クリーンアップ失敗: {f_path} - {e}")