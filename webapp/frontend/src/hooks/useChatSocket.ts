// WebSocket hook：clientId 变化时自动 connect/disconnect。
// onmessage → chatStore.handleEvent；不做自动重连（v1）。

import { useEffect, useRef } from "react";
import { useChatStore } from "../stores/chatStore";
import type { WsEnvelope } from "../api/chat-types";

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
      wsRef.current = null;
    };

    ws.onerror = () => {
      setWsState("closed");
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [clientId, handleEvent, setWsState, markStreamComplete]);
}
