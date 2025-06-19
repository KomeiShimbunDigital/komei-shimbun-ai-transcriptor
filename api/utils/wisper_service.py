import openai
import os
from typing import List, Dict
from pathlib import Path
import asyncio
import aiofiles
import time
from datetime import datetime

class WhisperService:
    def __init__(self, api_key: str = None):
        """
        OpenAI Whisper APIサービスの初期化
        """
        if api_key:
            openai.api_key = api_key
        else:
            # 環境変数から取得
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
        if not openai.api_key:
            raise ValueError("OpenAI API キーが設定されていません")
    
    async def transcribe_single_file(self, file_path: str, language: str = "ja") -> Dict:
        """
        単一ファイルの文字起こし
        """
        try:
            print(f"文字起こし開始: {file_path}")
            start_time = time.time()
            
            with open(file_path, "rb") as audio_file:
                # OpenAI Whisper APIを呼び出し
                response = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",  # タイムスタンプ付きで取得
                    temperature=0.0  # より一貫した結果のため
                )
            
            processing_time = time.time() - start_time
            
            result = {
                "file_path": file_path,
                "text": response.text,
                "language": response.language,
                "duration": response.duration,
                "processing_time": processing_time,
                "segments": getattr(response, 'segments', []),
                "success": True,
                "error": None
            }
            
            print(f"文字起こし完了: {file_path} ({processing_time:.2f}秒)")
            return result
            
        except Exception as e:
            print(f"文字起こしエラー: {file_path}, {e}")
            return {
                "file_path": file_path,
                "text": "",
                "success": False,
                "error": str(e),
                "processing_time": 0
            }
    
    async def transcribe_multiple_files(self, file_paths: List[str], language: str = "ja") -> List[Dict]:
        """
        複数ファイルの並列文字起こし
        """
        print(f"複数ファイルの文字起こし開始: {len(file_paths)}ファイル")
        
        # 並列処理のタスクを作成
        tasks = [
            self.transcribe_single_file(file_path, language) 
            for file_path in file_paths
        ]
        
        # 並列実行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外が発生した場合の処理
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "file_path": file_paths[i],
                    "text": "",
                    "success": False,
                    "error": str(result),
                    "processing_time": 0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def combine_transcriptions(self, transcription_results: List[Dict]) -> Dict:
        """
        複数の文字起こし結果を結合
        """
        try:
            # 成功した結果のみを抽出
            successful_results = [r for r in transcription_results if r.get("success", False)]
            
            if not successful_results:
                return {
                    "combined_text": "",
                    "success": False,
                    "error": "すべての文字起こしが失敗しました",
                    "total_duration": 0,
                    "total_processing_time": 0,
                    "segment_count": 0,
                    "combined_segments": []
                }
            
            # ファイル名でソート（part_000, part_001... の順序を保持）
            successful_results.sort(key=lambda x: x["file_path"])
            
            # テキストを結合
            combined_text_parts = []
            combined_segments_with_timestamps = [] # To store segments with timestamps
            total_duration = 0
            total_processing_time = 0
            segment_global_id = 0 # Global segment ID across all files
            
            for i, result in enumerate(successful_results):
                text = result.get("text", "").strip()
                if text:
                    # セグメント番号を追加（デバッグ用）
                    segment_header = f"\n--- セグメント {i+1} ---\n" if len(successful_results) > 1 else ""
                    combined_text_parts.append(f"{segment_header}{text}")

                # Process segments for timestamped output
                for segment in result.get("segments", []):
                    # Access attributes using dot notation instead of .get()
                    start_time = segment.start
                    end_time = segment.end
                    segment_text = segment.text.strip()
                    
                    # Format timestamp
                    start_min = int(start_time // 60)
                    start_sec = int(start_time % 60)
                    end_min = int(end_time // 60)
                    end_sec = int(end_time % 60)
                    timestamp_str = f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}]"
                    
                    combined_segments_with_timestamps.append(f"{timestamp_str} {segment_text}")
                    segment_global_id += 1
                
                total_duration += result.get("duration", 0)
                total_processing_time += result.get("processing_time", 0)
            
            combined_text = "\n\n".join(combined_text_parts)
            
            # 失敗したファイルの情報
            failed_results = [r for r in transcription_results if not r.get("success", False)]
            error_summary = ""
            if failed_results:
                error_summary = f"\n注意: {len(failed_results)}個のセグメントで文字起こしに失敗しました。"
            
            return {
                "combined_text": combined_text,
                "success": True,
                "error": error_summary if error_summary else None,
                "total_duration": total_duration,
                "total_processing_time": total_processing_time,
                "segment_count": segment_global_id, # Total number of individual segments
                "failed_count": len(failed_results),
                "detailed_results": transcription_results,
                "combined_segments": combined_segments_with_timestamps # New field
            }
            
        except Exception as e:
            return {
                "combined_text": "",
                "success": False,
                "error": f"結果の結合中にエラーが発生しました: {str(e)}",
                "total_duration": 0,
                "total_processing_time": 0,
                "segment_count": 0,
                "combined_segments": []
            }
    
    async def save_transcription_result(self, result: Dict, output_dir: str, user: str, original_filename: str) -> str:
        """
        文字起こし結果をファイルに保存
        """
        try:
            # 出力ディレクトリを作成
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # ファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{user}_{timestamp}_{Path(original_filename).stem}_transcription.txt"
            output_file_path = output_path / output_filename
            
            # ファイル内容を作成
            content_parts = [
                f"音声文字起こし結果",
                f"=" * 50,
                f"登録者: {user}",
                f"元ファイル: {original_filename}",
                f"処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"音声長: {result.get('total_duration', 0):.1f}秒",
                f"処理時間: {result.get('total_processing_time', 0):.1f}秒",
                f"セグメント数: {result.get('segment_count', 1)}",
                ""
            ]
            
            if result.get("error"):
                content_parts.append(f"注意事項: {result['error']}")
                content_parts.append("")
            
            content_parts.extend([
                "--- 全体書き起こし内容 ---",
                result.get("combined_text", ""),
                "",
                "--- セグメントごとのタイムスタンプとテキスト ---",
                "------------------------------------"
            ])

            # Add segmented text with timestamps
            for segment_line in result.get("combined_segments", []):
                content_parts.append(segment_line)
            
            content_parts.extend([
                "",
                f"処理完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])
            
            content = "\n".join(content_parts)
            
            # ファイルに保存
            async with aiofiles.open(output_file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            print(f"文字起こし結果を保存しました: {output_file_path}")
            return str(output_file_path)
            
        except Exception as e:
            print(f"結果保存エラー: {e}")
            return ""
    
    def get_api_usage_info(self) -> Dict:
        """
        API使用状況の情報を取得
        """
        return {
            "model": "whisper-1",
            "pricing_per_minute": 0.006,  # $0.006 per minute (2024年時点)
            "max_file_size": "25MB",
            "supported_formats": ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
        }