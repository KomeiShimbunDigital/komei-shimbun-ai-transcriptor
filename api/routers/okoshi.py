from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Annotated
import api.schemas.params as params
import asyncio
import os
import tempfile
from pathlib import Path
from datetime import datetime
import uuid
from starlette.responses import FileResponse
import glob
import shutil

# 必要なユーティリティをインポート
from api.utils.audio_utils import AudioProcessor
from api.utils.wisper_service import WhisperService

router = APIRouter()

openai_api_key = os.getenv('OPENAI_API_KEY')
print("KEY",openai_api_key)
# 初期化
audio_processor = AudioProcessor(output_dir="processed_audio")
whisper_service = WhisperService(openai_api_key)  # OPENAI_API_KEY環境変数が必要

def clean_directories_on_startup():
    """
    アプリケーション起動時に指定されたディレクトリ内のファイルを削除します。
    """
    directories_to_clean = [
        "processed_audio",
        "transcription_results"
    ]

    print("=== アプリケーション起動時のクリーンアップ開始 (from okoshi.py) ===")
    for directory in directories_to_clean:
        dir_path = Path(directory)
        if dir_path.exists() and dir_path.is_dir():
            print(f"🗑️ {directory}/ 配下のファイルを削除中...")
            try:
                for item in dir_path.iterdir():
                    if item.is_file():
                        os.remove(item)
                        print(f"  - 削除: {item}")
                    elif item.is_dir():
                        shutil.rmtree(item)
                        print(f"  - ディレクトリ削除: {item}")
                print(f"✓ {directory}/ のクリーンアップ完了。")
            except Exception as e:
                print(f"❌ {directory}/ のクリーンアップ中にエラーが発生しました: {e}")
        else:
            print(f"ℹ️ ディレクトリが存在しないか、ディレクトリではありません: {directory}/")
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True) # ディレクトリがない場合は作成
                print(f"✓ ディレクトリを作成しました: {directory}/")
    print("=== アプリケーション起動時のクリーンアップ完了 (from okoshi.py) ===")


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
    
    # 変換後のファイルパスを保持するための変数
    converted_file_path = None # ここで初期化

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
        
        print(f"File size from UploadFile object: {audio_file.size / (1024*1024):.2f} MB")
        print(f"Content type: {audio_file.content_type}")
        
        # ステップ1: ファイル内容を読み取り、保存
        file_content = await audio_file.read()

        # DEBUGログ追加
        print(f"DEBUG: Read file_content length: {len(file_content)} bytes")
        if len(file_content) == 0:
            print("DEBUG: CRITICAL! file_content is empty after read().")
            raise HTTPException(status_code=400, detail="アップロードされたファイルの内容が空です。")
        
        original_file_path = audio_processor.save_original_file(
            file_content=file_content, 
            original_filename=audio_file.filename, 
            user=user
        )
        print(f"✓ 元ファイル保存完了: {original_file_path}")

        # DEBUGログ追加
        try:
            saved_file_size = original_file_path.stat().st_size
            print(f"DEBUG: 保存されたファイルのサイズ: {saved_file_size} bytes")
            if saved_file_size == 0:
                print("DEBUG: WARNING! ファイルサイズが0です。書き込みに失敗している可能性があります。")
            
            with open(original_file_path, "rb") as f:
                header_bytes = f.read(64)
                print(f"DEBUG: ファイルの先頭バイト (hex): {header_bytes.hex()}")
                if header_bytes[:4].decode('ascii', errors='ignore') == "RIFF":
                    print("DEBUG: WAVファイルヘッダ 'RIFF' を確認しました。")
                else:
                    print("DEBUG: WARNING! WAVファイルヘッダ 'RIFF' を確認できませんでした。")

        except Exception as e:
            print(f"DEBUG: ファイル内容確認中にエラー: {e}")
        
        # ステップ2: 音声ファイルの検証と必要に応じたMP3変換
        is_valid, validation_message = audio_processor.validate_audio_file(original_file_path)
        print(f"✓ ファイル検証: {validation_message}")
        
        if not is_valid:
            # 検証失敗時はファイルを削除
            try:
                # os.remove(original_file_path) # デバッグのためコメントアウトを継続
                pass
            except:
                pass
            raise HTTPException(status_code=400, detail=validation_message)
        
        # ここでMP3への変換を試みる
        # convert_to_mp3_if_neededは、変換成功すると元のファイルを削除し、新しいMP3ファイルのパスを返す
        converted_file_path = audio_processor.convert_to_mp3_if_needed(original_file_path)
        print(f"✓ MP3変換/確認完了: {converted_file_path}")

        # 今後の処理はconverted_file_pathを使用するように変更する！！！
        process_target_file = converted_file_path # ここで正しいファイルパスを設定
        
        # ステップ3: 音声の長さをチェックし、必要に応じて分割
        # duration = audio_processor.get_audio_duration(original_file_path) # 古いパスを参照しているためNG
        duration = audio_processor.get_audio_duration(process_target_file) # ★★★ ここを修正 ★★★
        print(f"✓ 音声長: {duration/60:.1f}分")
        
        # 10分（600秒）を超える場合は分割
        if duration > 600:
            print("⚡ 音声が10分を超えています。分割処理を開始...")
            # 分割はMP3ファイルとして出力される
            split_files = audio_processor.split_audio(process_target_file, segment_length=600)
            print(f"✓ 分割完了: {len(split_files)}ファイル")
            # 分割された場合は、元の変換済みファイルはもう不要なので削除対象に含める
            files_to_clean_up_after_transcription = split_files + [process_target_file] # process_target_fileがconverted_file_pathなので追加
        else:
            split_files = [process_target_file]
            print("✓ 分割不要（10分以下）")
            files_to_clean_up_after_transcription = [process_target_file] # process_target_fileがconverted_file_pathなので追加


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
            original_filename=audio_file.filename # 元のファイル名を使用
        )
        print(f"✓ 結果ファイル保存完了: {result_file_path}")
        
        # ステップ7: 一時ファイルのクリーンアップ
        # ここで、分割ファイルと変換した一時ファイルを削除する
        # デバッグのためコメントアウトしている場合は、処理が成功したら忘れずに戻してください
        # audio_processor.cleanup_temp_files(files_to_clean_up_after_transcription, keep_original=False) # デバッグのためコメントアウトを継続
        # print("✓ 一時ファイルクリーンアップ完了")

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
                "file_path": str(result_file_path) # Pathオブジェクトを文字列に変換
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
            # デバッグのためコメントアウトしている場合は、処理が成功したら忘れずに戻してください
            # if 'original_file_path' in locals() and original_file_path.is_file():
            #     os.remove(original_file_path)
            # if converted_file_path and converted_file_path.is_file() and converted_file_path != original_file_path:
            #     os.remove(converted_file_path)
            # if 'split_files' in locals():
            #     audio_processor.cleanup_temp_files(split_files, keep_original=False)
            pass # コメントアウトした場合はpassを置く
        except Exception as cleanup_e:
            print(f"❌ エラー時のクリーンアップ失敗: {cleanup_e}")
            pass
        
        raise HTTPException(
            status_code=500, 
            detail=f"サーバー内部エラーが発生しました。ITサポートに連絡してください。(ID: {process_id})"
        )

@router.get("/download/transcription/{filename}")
async def download_transcription_file(filename: str):
    """
    指定された文字起こしファイルをダウンロード
    """
    # FastAPIがデコードしたファイル名をログに出力
    print(f"DEBUG: Download request received for filename (decoded): {filename}")

    # base_dirを先に絶対パスで定義
    base_dir_path_obj = Path("transcription_results").resolve()
    print(f"DEBUG: Base directory (resolved): {base_dir_path_obj}")

    file_path = base_dir_path_obj / filename
    print(f"DEBUG: Attempting to access full file_path: {file_path}")
    
    if not file_path.is_file():
        print(f"DEBUG: File NOT found at: {file_path}")
        # Dockerコンテナ内で実際にファイルが存在するか ls -l で確認するよう促す
        print(f"DEBUG: Please check inside Docker container: ls -l {base_dir_path_obj}/")
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    # Ensure the file is within the intended directory to prevent path traversal
    abs_file_path = file_path.resolve()
    print(f"DEBUG: Resolved file_path for security check: {abs_file_path}")
    
    # 絶対パスでのディレクトリトラバーサルチェック
    if not str(abs_file_path).startswith(str(base_dir_path_obj)):
        print(f"DEBUG: Security check failed: {abs_file_path} is not within {base_dir_path_obj}")
        raise HTTPException(status_code=400, detail="無効なファイルパスです")

    print(f"DEBUG: File found and path is valid. Serving file: {abs_file_path}")
    return FileResponse(path=abs_file_path, filename=filename, media_type="text/plain")