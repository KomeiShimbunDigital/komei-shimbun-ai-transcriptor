from fastapi import File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional

class ResponseParams(BaseModel):
    message: str = Field("", description="処理結果メッセージ")
    user: str = Field("", description="部署名・氏名")
    result_url: str = Field("", description="結果取得用URL")
    transcription_text: Optional[str] = Field("", description="文字起こし結果テキスト")
    processing_info: Optional[Dict[str, Any]] = Field(None, description="処理詳細情報")

# フォームデータを受け取るための関数パラメータ定義
# Pydanticモデルではなく、関数の引数として定義する
def get_form_params(
    user: Annotated[str, Form(description="部署名・氏名")] = "",
    audio_file: Annotated[UploadFile, File(description="テキスト化する音声ファイル (MP3, WAV, AAC)")] = None
):
    return {"user": user, "audio_file": audio_file}