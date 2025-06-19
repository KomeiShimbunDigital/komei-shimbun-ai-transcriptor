import os
import tempfile
from pathlib import Path
from typing import List, Tuple
import librosa
import soundfile as sf
from datetime import datetime
import hashlib

class AudioProcessor:
    def __init__(self, output_dir: str = "audio_files"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def save_original_file(self, file_content: bytes, filename: str, user: str) -> str:
        """
        アップロードされた音声ファイルを保存
        """
        # ファイル名を安全にする
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{user}_{timestamp}_{filename}"
        
        # ファイルパスを生成
        file_path = self.output_dir / safe_filename
        
        # ファイルを保存
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        return str(file_path)
    
    def get_audio_duration(self, file_path: str) -> float:
        """
        音声ファイルの長さを取得（秒）
        """
        try:
            y, sr = librosa.load(file_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            return duration
        except Exception as e:
            print(f"音声ファイルの読み込みエラー: {e}")
            return 0.0
    
    def split_audio(self, file_path: str, segment_length: int = 600) -> List[str]:
        """
        音声ファイルを指定された長さ（デフォルト10分=600秒）で分割
        """
        try:
            # 音声ファイルを読み込み
            y, sr = librosa.load(file_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # 分割が必要かチェック
            if duration <= segment_length:
                return [file_path]
            
            # 分割されたファイルのリスト
            split_files = []
            
            # ベースファイル名を取得
            base_path = Path(file_path)
            base_name = base_path.stem
            extension = base_path.suffix
            
            # 指定された長さで分割
            segment_samples = segment_length * sr
            total_samples = len(y)
            
            segment_count = 0
            for start_sample in range(0, total_samples, segment_samples):
                end_sample = min(start_sample + segment_samples, total_samples)
                segment_audio = y[start_sample:end_sample]
                
                # 分割ファイル名を生成
                segment_filename = f"{base_name}_part_{segment_count:03d}{extension}"
                segment_path = base_path.parent / segment_filename
                
                # 分割された音声を保存
                sf.write(str(segment_path), segment_audio, sr)
                split_files.append(str(segment_path))
                
                segment_count += 1
                
            print(f"音声ファイルを{segment_count}個のセグメントに分割しました")
            return split_files
            
        except Exception as e:
            print(f"音声分割エラー: {e}")
            return [file_path]  # エラーの場合は元ファイルを返す
    
    def validate_audio_file(self, file_path: str) -> Tuple[bool, str]:
        """
        音声ファイルの検証
        """
        try:
            # ファイルサイズチェック (500MB = 500 * 1024 * 1024 bytes)
            file_size = os.path.getsize(file_path)
            max_size = 500 * 1024 * 1024
            
            if file_size > max_size:
                return False, f"ファイルサイズが大きすぎます: {file_size / (1024*1024):.1f}MB (最大500MB)"
            
            # 音声ファイルとして読み込み可能かチェック
            y, sr = librosa.load(file_path, sr=None, duration=1.0)  # 最初の1秒だけ読み込み
            
            if len(y) == 0:
                return False, "音声データが空です"
            
            # 長さをチェック
            duration = self.get_audio_duration(file_path)
            if duration > 7200:  # 2時間以上
                return False, f"音声が長すぎます: {duration/60:.1f}分 (最大120分)"
            
            return True, f"音声ファイル検証成功: {duration/60:.1f}分, {file_size/(1024*1024):.1f}MB"
            
        except Exception as e:
            return False, f"音声ファイル検証エラー: {str(e)}"
    
    def cleanup_temp_files(self, file_paths: List[str], keep_original: bool = True):
        """
        一時ファイルのクリーンアップ
        """
        for file_path in file_paths:
            try:
                # 元ファイルは保持する場合はスキップ
                if keep_original and not "_part_" in file_path:
                    continue
                    
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"クリーンアップ: {file_path}")
            except Exception as e:
                print(f"ファイル削除エラー: {file_path}, {e}")
    
    def get_file_info(self, file_path: str) -> dict:
        """
        ファイル情報を取得
        """
        try:
            file_size = os.path.getsize(file_path)
            duration = self.get_audio_duration(file_path)
            
            return {
                "file_path": file_path,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "duration_minutes": round(duration / 60, 2),
                "duration_seconds": round(duration, 2)
            }
        except Exception as e:
            return {
                "file_path": file_path,
                "error": str(e)
            }