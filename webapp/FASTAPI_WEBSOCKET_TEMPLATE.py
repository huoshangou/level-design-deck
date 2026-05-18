"""
FastAPI + Claude Agent SDK WebSocket Handler Template
For level-design-deck Phase 2 stateful chat integration.

Usage:
1. Add to backend/app.py: from .websocket_handler import router; app.include_router(router)
2. Frontend WebSocket connect: ws://localhost:5173/ws/user123
3. Send JSON: {"prompt": "Read specs directory"}
4. Receive JSON: {"type": "token" | "result" | "error", "text": "..."}
"""

import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    SystemMessage,
    ResultMessage,
    AssistantMessage,
    ProcessError,
    HookMatcher,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Session storage: client_id -> session_id
active_sessions: Dict[str, str] = {}


async def bash_command_whitelist(input_data, tool_use_id, context):
    """
    Whitelist Bash commands to prevent malicious execution.
    Called via PreToolUse hook before Bash tool runs.
    """
    cmd = input_data.get("tool_input", {}).get("command", "")
    
    # Define allowed command prefixes
    ALLOWED_PREFIXES = [
        "python3 tools/",
        "ls specs/",
        "ls outputs/",
        "cat outputs/",
        "grep ",
        "find specs/",
    ]
    
    if not any(cmd.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        logger.warning(f"[BASH-BLOCKED] {cmd}")
        raise PermissionError(f"Command blocked by whitelist: {cmd[:50]}")
    
    logger.debug(f"[BASH-ALLOWED] {cmd[:60]}...")
    return {}


async def intercept_file_write(input_data, tool_use_id, context):
    """
    Log file modifications.
    Called via PostToolUse hook after Write/Edit tool completes.
    """
    file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
    logger.info(f"[FILE-MODIFIED] {file_path}")
    return {}


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(ws: WebSocket, client_id: str):
    """
    WebSocket endpoint for stateful chat with Claude Agent SDK.
    
    Each client_id gets a persistent session that remembers context across messages.
    """
    await ws.accept()
    agent_options = None
    
    try:
        # Initialize or retrieve session
        if client_id not in active_sessions:
            logger.info(f"[INIT] New session for client {client_id}")
            
            # Create new session by running an empty query
            async for msg in query(
                prompt="",  # Empty to just initialize
                options=ClaudeAgentOptions(
                    allowed_tools=["Bash", "Read", "Write", "Edit"],
                    cwd="/Users/mofashu/Desktop/level-design-deck",
                    max_turns=0,  # Don't execute anything
                ),
            ):
                if isinstance(msg, SystemMessage) and msg.subtype == "init":
                    session_id = msg.data.get("session_id")
                    active_sessions[client_id] = session_id
                    logger.info(f"[SESSION] {client_id} -> {session_id}")
                    break
        
        # Configure agent options with hooks
        session_id = active_sessions[client_id]
        agent_options = ClaudeAgentOptions(
            allowed_tools=["Bash", "Read", "Write", "Edit"],
            resume=session_id,
            cwd="/Users/mofashu/Desktop/level-design-deck",
            max_turns=10,
            hooks={
                "PreToolUse": [
                    HookMatcher(matcher="Bash", hooks=[bash_command_whitelist]),
                ],
                "PostToolUse": [
                    HookMatcher(matcher="Write|Edit", hooks=[intercept_file_write]),
                ],
            },
        )
        
        # Message loop
        while True:
            # Receive user prompt
            data = await ws.receive_text()
            try:
                request = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "text": "Invalid JSON"})
                continue
            
            prompt = request.get("prompt", "").strip()
            if not prompt:
                await ws.send_json({"type": "error", "text": "Prompt required"})
                continue
            
            logger.info(f"[QUERY] {client_id} -> {prompt[:60]}...")
            
            # Process query
            try:
                async for msg in query(prompt=prompt, options=agent_options):
                    if isinstance(msg, ResultMessage):
                        # Final result
                        await ws.send_json({
                            "type": "result",
                            "text": msg.result,
                        })
                    elif isinstance(msg, AssistantMessage):
                        # Claude's streaming response
                        for block in msg.content:
                            # block.text contains streamed token(s)
                            if hasattr(block, "text"):
                                await ws.send_json({
                                    "type": "token",
                                    "text": block.text,
                                })
                    elif isinstance(msg, SystemMessage):
                        if msg.subtype == "error":
                            logger.error(f"System error: {msg.data}")
                            await ws.send_json({
                                "type": "error",
                                "text": f"System error: {msg.data}",
                            })
            
            except ProcessError as e:
                # Claude Code CLI crashed
                logger.error(f"[CRASH] {client_id}: exit code {e.exit_code}")
                active_sessions.pop(client_id, None)
                await ws.send_json({
                    "type": "error",
                    "text": f"Agent crashed (exit {e.exit_code}). Reconnect to restart.",
                })
                break
            
            except PermissionError as e:
                # Hook blocked operation
                await ws.send_json({
                    "type": "error",
                    "text": f"Operation blocked: {str(e)}",
                })
    
    except WebSocketDisconnect:
        logger.info(f"[DISCONNECT] {client_id}")
    
    except Exception as e:
        logger.exception(f"Unexpected error for {client_id}: {e}")
        await ws.send_json({
            "type": "error",
            "text": f"Server error: {str(e)}",
        })
    
    finally:
        # Cleanup
        if client_id in active_sessions:
            del active_sessions[client_id]
            logger.info(f"[CLEANUP] Removed session for {client_id}")


@router.get("/api/sessions")
async def list_sessions():
    """Debug endpoint: list active sessions."""
    return {
        "active_clients": list(active_sessions.keys()),
        "count": len(active_sessions),
    }
