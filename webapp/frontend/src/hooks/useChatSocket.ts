// WebSocket hook：clientId 变化时自动 connect/disconnect。
// onmessage → chatStore.handleEvent；不做自动重连（v1）。

import { useEffect, useRef } from "react";
import { useChatStore } from "../stores/chatStore";
import type { WsEnvelope } from "../api/chat-types";

// 模块级 WS 引用：让 store / 组件能在不 prop drilling 的情况下推帧给后端。
// 多 tab 不是问题——每个 tab 自己一份 module scope。
let activeWs: WebSocket | null = null;

/** 给后端发 interrupt 帧。WS 没开 / 没在 streaming 都安全 no-op，返回是否真发出去了。 */
export function sendInterrupt(): boolean {
  if (activeWs && activeWs.readyState === WebSocket.OPEN) {
    activeWs.send(JSON.stringify({ type: "interrupt" }));
    return true;
  }
  return false;
}

export function useChatSocket(clientId: string | null) {
  const { handleEvent, setWsState, markStreamComplete } = useChatStore();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // close old connection when clientId changes / unmounts
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (!clientId) return;

    const url = `ws://${location.host}/ws/chat/${encodeURIComponent(clientId)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    activeWs = ws;

    ws.onopen = () => {
      setWsState("open");
    };

    ws.onmessage = (evt) => {
      let envelope: WsEnvelope;
      try {
        envelope = JSON.parse(evt.data as string) as WsEnvelope;
      } catch {
        return;
      }
      handleEvent(envelope);
    };

    ws.onclose = () => {
      setWsState("closed");
      // flush any pending partial turn on unexpected close
      markStreamComplete();
      if (activeWs === ws) activeWs = null;
      wsRef.current = null;
    };

    ws.onerror = () => {
      setWsState("closed");
    };

    return () => {
      ws.close();
      if (activeWs === ws) activeWs = null;
      wsRef.current = null;
    };
  }, [clientId, handleEvent, setWsState, markStreamComplete]);
}
