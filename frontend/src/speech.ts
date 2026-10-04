/** Web Speech API 封装：TTS 朗读 + STT 听写。浏览器能力检测 + 键盘兜底。 */
import { useEffect, useState } from "react";

/* eslint-disable @typescript-eslint/no-explicit-any */

function pickEnVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  const en = voices.filter((v) => v.lang.startsWith("en"));
  if (!en.length) return null;
  const prefer = ["Google US English", "Microsoft Aria", "Microsoft Zira", "Samantha"];
  for (const name of prefer) {
    const hit = en.find((v) => v.name.includes(name));
    if (hit) return hit;
  }
  return en[0];
}

/** 朗读一段英文（中文行传 zh-CN）。不排队：先清空再朗读。 */
export function speak(text: string, lang: "en-US" | "zh-CN" = "en-US"): void {
  if (!("speechSynthesis" in window)) return;
  const synth = window.speechSynthesis;
  synth.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = lang === "en-US" ? 0.85 : 1;
  if (lang === "en-US") {
    const v = pickEnVoice();
    if (v) u.voice = v;
  }
  synth.speak(u);
}

export function stopSpeaking(): void {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

/** STT 能力检测（Chrome/Edge 的 webkitSpeechRecognition）。 */
export function sttSupported(): boolean {
  const w = window as any;
  return Boolean(w.SpeechRecognition || w.webkitSpeechRecognition);
}

/** 听一句英文：说停自动结束，resolve 转写文本；不支持/失败/超时 reject。 */
export function listenOnce(): Promise<string> {
  return new Promise((resolve, reject) => {
    const w = window as any;
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SR) {
      reject(new Error("此浏览器不支持语音识别，请用键盘输入"));
      return;
    }
    const rec = new SR();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    const timer = window.setTimeout(() => {
      rec.stop();
      reject(new Error("没有听到声音，再试一次好吗？"));
    }, 8000);
    rec.onresult = (e: any) => {
      window.clearTimeout(timer);
      const transcript = e.results[0][0].transcript;
      resolve(transcript);
    };
    rec.onerror = (e: any) => {
      window.clearTimeout(timer);
      reject(new Error(e?.error === "not-allowed" ? "需要允许使用麦克风" : "没有听清，再试一次好吗？"));
    };
    rec.onend = () => window.clearTimeout(timer);
    try {
      rec.start();
    } catch {
      reject(new Error("麦克风启动失败，再试一次好吗？"));
    }
  });
}

/** 首次挂载后返回声音列表是否就绪（触发 Chrome 异步 voices 加载）。 */
export function useVoicesReady(): boolean {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const synth = window.speechSynthesis;
    const warm = () => setReady(synth.getVoices().length > 0);
    warm();
    synth.addEventListener("voiceschanged", warm);
    return () => synth.removeEventListener("voiceschanged", warm);
  }, []);
  return ready;
}
