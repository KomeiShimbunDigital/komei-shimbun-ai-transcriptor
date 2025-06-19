from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Annotated
import api.schemas.params as params
import asyncio
import os
import tempfile
from pathlib import Path
from datetime import datetime
import uuid

# 必要なユーティリティをインポート
from api.utils.audio_utils import AudioProcessor
from api.utils.wisper_service import WhisperService

router = APIRouter()

openai_api_key = os.getenv('OPENAI_API_KEY')
print("KEY",openai_api_key)
# 初期化
audio_processor = AudioProcessor(output_dir="processed_audio")
whisper_service = WhisperService(openai_api_key)  # OPENAI_API_KEY環境変数が必要

@router.post("/okoshi", response_model=params.ResponseParams)
async def okoshi_process(
    user: Annotated[str, Form(description="部署名・氏名")] = "",
    audio_file: Annotated[UploadFile, File(description="テキスト化する音声ファイル")] = None
):
    """
    音声ファイルのアップロードと文字起こし処理
    """
    # 処理ID生成
    process_id = str(uuid.uuid4())[:8]
    
    try:
        print(f"=== 音声処理開始 ===")
        print(f"処理ID: {process_id}")
        print(f"User: {user}")
        print(f"Audio file: {audio_file.filename if audio_file else 'None'}")
        
        # 入力検証
        if not user or not user.strip():
            raise HTTPException(status_code=400, detail="登録者名が入力されていません")
        
        if not audio_file:
            raise HTTPException(status_code=400, detail="音声ファイルがアップロードされていません")
        
        if audio_file.size == 0:
            raise HTTPException(status_code=400, detail="空のファイルです")
        
        print(f"File size: {audio_file.size / (1024*1024):.2f} MB")
        print(f"Content type: {audio_file.content_type}")
        
        # ステップ1: ファイル内容を読み取り、保存
        file_content = await audio_file.read()
        
        # 元ファイルを保存
        original_file_path = audio_processor.save_original_file(
            file_content, 
            audio_file.filename, 
            user
        )
        print(f"✓ 元ファイル保存完了: {original_file_path}")
        
        # ステップ2: 音声ファイルの検証
        is_valid, validation_message = audio_processor.validate_audio_file(original_file_path)
        print(f"✓ ファイル検証: {validation_message}")
        
        if not is_valid:
            # 検証失敗時はファイルを削除
            try:
                os.remove(original_file_path)
            except:
                pass
            raise HTTPException(status_code=400, detail=validation_message)
        
        # ステップ3: 音声の長さをチェックし、必要に応じて分割
        duration = audio_processor.get_audio_duration(original_file_path)
        print(f"✓ 音声長: {duration/60:.1f}分")
        
        # 10分（600秒）を超える場合は分割
        if duration > 600:
            print("⚡ 音声が10分を超えています。分割処理を開始...")
            split_files = audio_processor.split_audio(original_file_path, segment_length=600)
            print(f"✓ 分割完了: {len(split_files)}ファイル")
        else:
            split_files = [original_file_path]
            print("✓ 分割不要（10分以下）")
        
        # ステップ4: OpenAI Whisperで文字起こし
        print("🎤 OpenAI Whisperで文字起こし開始...")
        transcription_results = await whisper_service.transcribe_multiple_files(
            split_files, 
            language="ja"
        )
        
        # ステップ5: 結果をまとめる
        combined_result = whisper_service.combine_transcriptions(transcription_results)
        
        if not combined_result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"文字起こしに失敗しました: {combined_result.get('error', '不明なエラー')}"
            )
        
        print(f"✓ 文字起こし完了: {combined_result['segment_count']}セグメント")
        print(f"  - 総処理時間: {combined_result['total_processing_time']:.1f}秒")
        print(f"  - 総音声長: {combined_result['total_duration']:.1f}秒")
        
        # ステップ6: 結果をファイルに保存
        result_file_path = await whisper_service.save_transcription_result(
            combined_result,
            output_dir="transcription_results",
            user=user,
            original_filename=audio_file.filename
        )
        print(f"✓ 結果ファイル保存完了: {result_file_path}")
        
        # ステップ7: 一時ファイルのクリーンアップ（分割ファイルのみ削除）
        if len(split_files) > 1:
            audio_processor.cleanup_temp_files(split_files, keep_original=True)
            print("✓ 一時ファイルクリーンアップ完了")
        
        # レスポンス準備
        response = {
            "message": "文字起こしが完了しました！",
            "user": user,
            "result_url": f"/result/{process_id}",
            "transcription_text": combined_result["combined_text"],
            "processing_info": {
                "duration_minutes": round(combined_result["total_duration"] / 60, 2),
                "processing_time_seconds": round(combined_result["total_processing_time"], 2),
                "segment_count": combined_result["segment_count"],
                "file_path": result_file_path
            }
        }
        
        print(f"=== 音声処理完了 (ID: {process_id}) ===")
        return response
        
    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        print(f"❌ 予期せぬエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # エラー時のクリーンアップ
        try:
            if 'original_file_path' in locals():
                os.remove(original_file_path)
            if 'split_files' in locals():
                audio_processor.cleanup_temp_files(split_files, keep_original=False)
        except:
            pass
        
        raise HTTPException(
            status_code=500, 
            detail=f"サーバー内部エラーが発生しました。ITサポートに連絡してください。(ID: {process_id})"
        )