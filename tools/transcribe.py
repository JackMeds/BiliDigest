import sys
import os
import argparse
import time
import json
import warnings
from pathlib import Path
from .utils import check_environment

# Suppress warnings
warnings.filterwarnings("ignore")

try:
    import google.generativeai as genai
except ImportError:
    genai = None

def transcribe_gemini(file_path):
    """Use Google Gemini to transcribe/analyze video directly."""
    if not genai:
        print("❌ google-generativeai not installed. Run: pip install google-generativeai")
        return None
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables.")
        return None
        
    genai.configure(api_key=api_key)
    
    print(f"   📤 Uploading {file_path.name} to Gemini (Multimodal)...")
    # Upload file
    try:
        video_file = genai.upload_file(path=file_path)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None
    
    # Wait for processing
    print("   ⏳ Processing video...")
    while video_file.state.name == "PROCESSING":
        print('.', end='', flush=True)
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
        
    if video_file.state.name == "FAILED":
        print("\n❌ Google Server failed to process file.")
        return None
    
    print("\n   🤖 Analyzing with Gemini 1.5 Flash...")
    # Using 1.5 Flash by default as it's fast and supports video
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    prompt = "Please provide a verbatim transcription of this video/audio. If there are visual elements, describe them briefly in brackets."
    
    try:
        response = model.generate_content([video_file, prompt])
        return response.text
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return None

def transcribe_openai(audio_path, model_name="whisper-1", language="zh"):
    """使用 OpenAI API 转录"""
    try:
        from openai import OpenAI
    except ImportError:
        print("❌ openai package not installed")
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    
    if not api_key:
        print("❌ 未配置 OPENAI_API_KEY")
        return None
        
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    print(f"☁️ 使用 API ({model_name}) 转录中...")
    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model=model_name,
                file=f,
                response_format="verbose_json",
                language=language if language != "auto" else None
            )
        return transcript.text
    except Exception as e:
        print(f"❌ API 错误: {e}")
        return None

def transcribe_local(audio_path, model_name, language):
    """使用本地模型转录 (Whisper/Qwen)"""
    device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1" else "cpu"
    # 简单检测 cuda
    try:
        import torch
        if torch.cuda.is_available(): device = "cuda"
    except: pass
    
    print(f"🖥️ 使用本地模型 ({model_name}) 设备: {device}")

    if "qwen" in model_name.lower():
        # Transformers pipeline for Qwen
        try:
            from transformers import pipeline
            pipe = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                device=device,
                trust_remote_code=True
            )
            result = pipe(str(audio_path), chunk_length_s=30, batch_size=8)
            return result["text"]
        except Exception as e:
            print(f"❌ Qwen 加载失败: {e}")
            return None
    else:
        # Faster Whisper
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(model_name, device=device, compute_type="float16" if device=="cuda" else "int8")
            segments, info = model.transcribe(str(audio_path), language=language, beam_size=5)
            
            text = []
            print(f"检测语言: {info.language} (概率: {info.language_probability:.2f})")
            for segment in segments:
                print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
                text.append(segment.text)
            return "\n".join(text)
        except Exception as e:
            print(f"❌ Whisper 出错: {e}")
            return None

if __name__ == "__main__":
    check_environment("transcribe")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except: pass

    parser = argparse.ArgumentParser(description="语音/视频转写工具")
    parser.add_argument("file", help="音频/视频文件路径")
    parser.add_argument("--model", "-m", default="base", help="模型名称 (base/large-v3/openai/gemini/Qwen...)")
    parser.add_argument("--language", "-l", default="zh", help="语言代码 (仅Whisper有效)")
    
    args = parser.parse_args()
    
    path = Path(args.file)
    if not path.exists():
        print("❌ 文件不存在")
        sys.exit(1)
        
    model_lower = args.model.lower()
    
    if "gemini" in model_lower:
        text = transcribe_gemini(path)
    elif model_lower in ["openai", "whisper-1"]:
        text = transcribe_openai(path, "whisper-1", args.language)
    else:
        text = transcribe_local(path, args.model, args.language)
        
    if text:
        out_path = path.with_suffix(".txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\n✅ 转录完成! 已保存至: {out_path}")
